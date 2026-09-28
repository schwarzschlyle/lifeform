from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Any

import numpy as np

from lifeform.biology.body import BodyState
from lifeform.biology.disease import InfectionState
from lifeform.biology.genome import GENES, Genome
from lifeform.biology.inheritance import Inheritance
from lifeform.biology.instincts import INSTINCT_KEYS
from lifeform.biology.lineage import Lineage
from lifeform.biology.mechanics import BodyMechanics
from lifeform.biology.naming import IndividualNamer
from lifeform.biology.organism import Organism, OrganismIdentity
from lifeform.biology.phenotype import Development, Phenotype
from lifeform.biology.reproduction import ReproductiveState, Sex
from lifeform.biology.social import SocialState
from lifeform.config.parameters import EcologyParameters
from lifeform.core.geometry import Direction, Position, TorusMetric
from lifeform.core.identifiers import IdSequence
from lifeform.perception.memory import AssociativeLearner, EpisodicMemory, MemorySystem, SocialMemory, SpatialMemory

EXPRESSED_INSTINCT_VALUE = 0.85
LATENT_INSTINCT_VALUE = 0.2
DEFAULT_GENE_VALUE = 0.5
FOUNDER_ENERGY_FRACTION = 0.7
FOUNDER_HYDRATION = 0.9
FOUNDER_MIN_AGE_FRACTION_OF_LIFESPAN = 0.5
RATING_NOISE = 50.0


@dataclass(frozen=True, slots=True)
class Archetype:
    slug: str
    name: str
    hue: float
    base_genotype: np.ndarray

    @classmethod
    def from_mapping(cls, data: dict[str, Any], overrides: dict[str, float]) -> Archetype:
        genotype = np.full(GENES.size, DEFAULT_GENE_VALUE, dtype=np.float32)
        for key in INSTINCT_KEYS:
            genotype[GENES.index[f"instinct:{key}"]] = LATENT_INSTINCT_VALUE
        marker_rng = np.random.default_rng(int.from_bytes(hashlib.sha256(data["slug"].encode()).digest()[:8], "little"))
        for index in GENES.neutral_indices():
            genotype[index] = float(marker_rng.random())
        genes = {**data.get("genes", {}), **overrides}
        for name, value in genes.items():
            genotype[GENES.index[name]] = GENES.spec(name).encode(float(value))
        for key in data.get("instincts", []):
            genotype[GENES.index[f"instinct:{key}"]] = EXPRESSED_INSTINCT_VALUE
        genotype[GENES.index["coat_hue"]] = float(data.get("hue", genotype[GENES.index["coat_hue"]]))
        return cls(data["slug"], data["name"], float(data.get("hue", 0.5)), genotype)


class OrganismFactory:
    def __init__(
        self,
        ecology: EcologyParameters,
        metric: TorusMetric,
        mechanics: BodyMechanics,
        rng: np.random.Generator,
        ids: IdSequence,
    ) -> None:
        self._ecology = ecology
        self._metric = metric
        self._mechanics = mechanics
        self._rng = rng
        self._ids = ids
        self._development = Development(ecology, rng)
        self._inheritance = Inheritance(ecology.evolution, rng)
        self._namer = IndividualNamer(rng)

    def founder(
        self, archetype: Archetype, species_id: int, position: Position, tick: int, local_temperature_c: float
    ) -> Organism:
        noise = self._ecology.evolution.founder_allele_noise
        alleles = archetype.base_genotype[None, :] + self._rng.normal(0.0, noise, (2, GENES.size)) * GENES.variation
        alleles[:, GENES.index["sex_ratio_bias"]] = DEFAULT_GENE_VALUE
        genome = Genome(alleles.astype(np.float32))
        phenotype = self._development.develop(genome)
        organism_id = self._ids.next()
        age = int(
            self._rng.uniform(
                phenotype.maturity_ticks,
                max(phenotype.maturity_ticks + 1.0, FOUNDER_MIN_AGE_FRACTION_OF_LIFESPAN * phenotype.lifespan_ticks),
            )
        )
        body = self._body(phenotype, position, phenotype.adult_mass_kg, age, local_temperature_c)
        organism = Organism(
            identity=OrganismIdentity(organism_id, self._namer.name(), species_id, tick - age, archetype.slug),
            genome=genome,
            phenotype=phenotype,
            body=body,
            reproduction=self._reproduction(mature=True),
            infection=InfectionState(),
            social=self._social(),
            lineage=Lineage.founder(organism_id),
            memory=self._memory(phenotype),
        )
        body.energy_eu = FOUNDER_ENERGY_FRACTION * self._mechanics.energy_capacity(organism)
        body.hydration = FOUNDER_HYDRATION
        return organism

    def offspring(
        self, mother: Organism, father_genome: Genome, father_lineage: Lineage, birth_mass_kg: float, tick: int
    ) -> Organism:
        genome = self._inheritance.offspring(mother.genome, father_genome)
        phenotype = self._development.develop(genome)
        organism_id = self._ids.next()
        position = mother.body.position
        mass = max(self._ecology.development.birth_mass_floor_kg, birth_mass_kg)
        body = self._body(phenotype, position, mass, 0, mother.body.body_temperature_c)
        reproduction = self._reproduction(mature=False)
        reproduction.mother_id = mother.id
        organism = Organism(
            identity=OrganismIdentity(organism_id, self._namer.name(), mother.species_id, tick, None),
            genome=genome,
            phenotype=phenotype,
            body=body,
            reproduction=reproduction,
            infection=InfectionState(),
            social=self._social(),
            lineage=Lineage.offspring(organism_id, mother.lineage, father_lineage),
            memory=self._memory(phenotype),
        )
        body.energy_eu = self._ecology.reproduction.newborn_reserve_fraction * self._mechanics.energy_capacity(organism)
        body.hydration = 1.0
        body.in_den = mother.body.in_den
        return organism

    def _body(self, phenotype: Phenotype, position: Position, mass: float, age: int, temperature_c: float) -> BodyState:
        endothermy = phenotype.endothermy
        body_temperature = endothermy * self._ecology.thermal.endotherm_set_point_c + (1.0 - endothermy) * (
            temperature_c
        )
        return BodyState(
            position=position,
            heading=Direction(int(self._rng.integers(8))),
            mass_kg=mass,
            lean_mass_kg=mass,
            energy_eu=0.0,
            hydration=1.0,
            body_temperature_c=body_temperature,
            age_ticks=age,
        )

    def _reproduction(self, mature: bool) -> ReproductiveState:
        sex = Sex.FEMALE if self._rng.random() < DEFAULT_GENE_VALUE else Sex.MALE
        cycle = self._ecology.reproduction.estrus_cycle_ticks
        return ReproductiveState(sex=sex, estrus_offset=int(self._rng.integers(cycle)), mature=mature, weaned=mature)

    def _social(self) -> SocialState:
        return SocialState(rating=self._ecology.social.initial_rating + float(self._rng.normal(0.0, RATING_NOISE)))

    def _memory(self, phenotype: Phenotype) -> MemorySystem:
        memory = self._ecology.memory
        capacity = phenotype.trait("memory_capacity")
        spatial_slots = round(
            memory.min_spatial_slots + (memory.max_spatial_slots - memory.min_spatial_slots) * capacity
        )
        social_slots = round(memory.min_social_slots + (memory.max_social_slots - memory.min_social_slots) * capacity)
        half_life = memory.min_half_life_ticks + (memory.max_half_life_ticks - memory.min_half_life_ticks) * capacity
        return MemorySystem(
            spatial=SpatialMemory(spatial_slots, half_life, self._metric),
            social=SocialMemory(social_slots),
            episodic=EpisodicMemory(memory.episodic_slots),
            associations=AssociativeLearner(phenotype.trait("learning_rate"), memory.habituation_rate),
        )
