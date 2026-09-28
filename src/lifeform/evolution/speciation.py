from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field

import numpy as np

from lifeform.biology.genome import GENES, Genome, genotype_distance
from lifeform.biology.naming import SpeciesNamer
from lifeform.biology.organism import Organism
from lifeform.biology.phenotype import Development
from lifeform.config.parameters import EvolutionParameters
from lifeform.core.identifiers import IdSequence

HUE_DRIFT = 0.06


@dataclass(slots=True)
class Species:
    species_id: int
    name: str
    parent_id: int | None
    origin_tick: int
    representative: np.ndarray
    hue: float
    archetype: str | None
    extinct_tick: int | None = None
    peak_population: int = 0
    member_history: list[tuple[int, int]] = field(default_factory=list)

    @property
    def alive(self) -> bool:
        return self.extinct_tick is None


@dataclass(slots=True)
class PendingCluster:
    centroid: np.ndarray
    members: list[int]
    rounds: int = 1


@dataclass(frozen=True, slots=True)
class SpeciationEvent:
    kind: str
    species_id: int
    parent_id: int | None
    tick: int
    name: str


class SpeciesRegistry:
    def __init__(self) -> None:
        self._ids = IdSequence()
        self.species: dict[int, Species] = {}
        self._namer = SpeciesNamer()

    def found(
        self, name: str, representative: np.ndarray, hue: float, tick: int, parent_id: int | None, archetype: str | None
    ) -> Species:
        species = Species(self._ids.next(), name, parent_id, tick, representative.copy(), hue, archetype)
        self.species[species.species_id] = species
        return species

    def name_of(self, species_id: int) -> str:
        species = self.species.get(species_id)
        return species.name if species is not None else "unknown animal"

    def living(self) -> list[Species]:
        return [species for species in self.species.values() if species.alive]

    def new_name(self, development: Development, representative: np.ndarray) -> str:
        phenotype = development.develop(Genome(np.stack([representative, representative])))
        return self._namer.name(phenotype)


class SpeciesClusterer:
    def __init__(self, parameters: EvolutionParameters, registry: SpeciesRegistry, development: Development) -> None:
        self._parameters = parameters
        self._registry = registry
        self._development = development
        self._pending: list[PendingCluster] = []

    def cluster(self, organisms: list[Organism], tick: int) -> list[SpeciationEvent]:
        events: list[SpeciationEvent] = []
        living = self._registry.living()
        unassigned: list[Organism] = []
        members: dict[int, list[Organism]] = {species.species_id: [] for species in living}
        for organism in organisms:
            nearest = self._nearest(organism.genome.genotype, living)
            if nearest is None:
                unassigned.append(organism)
            else:
                members[nearest.species_id].append(organism)
        events.extend(self._promote_candidates(unassigned, tick, members))
        for species in living:
            group = members.get(species.species_id, [])
            for organism in group:
                organism.identity.species_id = species.species_id
            if group:
                species.representative = self._medoid(group)
                species.peak_population = max(species.peak_population, len(group))
            species.member_history.append((tick, len(group)))
        events.extend(self._extinctions(tick, organisms))
        return events

    def _nearest(self, genotype: np.ndarray, living: list[Species]) -> Species | None:
        best: Species | None = None
        best_distance = self._parameters.species_distance
        for species in living:
            distance = genotype_distance(genotype, species.representative)
            if distance < best_distance:
                best, best_distance = species, distance
        return best

    def _promote_candidates(
        self, unassigned: list[Organism], tick: int, members: dict[int, list[Organism]]
    ) -> list[SpeciationEvent]:
        clusters = self._leader_clusters(unassigned)
        carried: list[PendingCluster] = []
        events: list[SpeciationEvent] = []
        for group in clusters:
            centroid = np.mean([organism.genome.genotype for organism in group], axis=0).astype(np.float32)
            previous = self._matching_pending(centroid)
            rounds = previous.rounds + 1 if previous is not None else 1
            if rounds >= self._parameters.species_persistence_rounds and len(group) >= (
                self._parameters.species_min_members
            ):
                species = self._register(group, tick)
                members[species.species_id] = group
                events.append(SpeciationEvent("speciation", species.species_id, species.parent_id, tick, species.name))
            else:
                carried.append(PendingCluster(centroid, [organism.id for organism in group], rounds))
        self._pending = carried
        return events

    def _leader_clusters(self, organisms: list[Organism]) -> list[list[Organism]]:
        clusters: list[tuple[np.ndarray, list[Organism]]] = []
        for organism in organisms:
            genotype = organism.genome.genotype
            for leader, group in clusters:
                if genotype_distance(genotype, leader) < self._parameters.species_distance:
                    group.append(organism)
                    break
            else:
                clusters.append((genotype, [organism]))
        return [group for _, group in clusters]

    def _matching_pending(self, centroid: np.ndarray) -> PendingCluster | None:
        for pending in self._pending:
            if genotype_distance(centroid, pending.centroid) < self._parameters.species_distance:
                return pending
        return None

    def _register(self, group: list[Organism], tick: int) -> Species:
        parent_id = Counter(organism.species_id for organism in group).most_common(1)[0][0]
        parent = self._registry.species.get(parent_id)
        representative = self._medoid(group)
        hue = ((parent.hue if parent else 0.5) + HUE_DRIFT * (1 if len(self._registry.species) % 2 else -1)) % 1.0
        name = self._registry.new_name(self._development, representative)
        return self._registry.found(name, representative, hue, tick, parent_id, parent.archetype if parent else None)

    @staticmethod
    def _medoid(group: list[Organism]) -> np.ndarray:
        genotypes = np.array([organism.genome.genotype for organism in group], dtype=np.float32)
        centroid = genotypes.mean(axis=0)
        distances = np.sqrt(((genotypes - centroid) ** 2 * GENES.distance_weights).sum(axis=1))
        return genotypes[int(np.argmin(distances))].copy()

    def _extinctions(self, tick: int, organisms: list[Organism]) -> list[SpeciationEvent]:
        present = {organism.species_id for organism in organisms}
        events: list[SpeciationEvent] = []
        for species in self._registry.living():
            if species.species_id not in present:
                species.extinct_tick = tick
                events.append(SpeciationEvent("extinction", species.species_id, species.parent_id, tick, species.name))
        return events
