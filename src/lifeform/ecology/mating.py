from __future__ import annotations

import math

import numpy as np

from lifeform.biology.mechanics import BodyMechanics
from lifeform.biology.organism import Organism
from lifeform.biology.reproduction import Pregnancy
from lifeform.config.parameters import EcologyParameters

SENESCENT_FERTILITY = 0.5
BURDEN_REFERENCE_MASS_FRACTION = 0.1


class ConceptionModel:
    def __init__(self, ecology: EcologyParameters, mechanics: BodyMechanics, rng: np.random.Generator) -> None:
        self._ecology = ecology
        self._mechanics = mechanics
        self._rng = rng

    def compatibility(self, mother: Organism, father: Organism) -> float:
        distance = mother.genome.distance(father.genome)
        isolation = self._ecology.reproduction.isolation_distance
        return max(0.0, 1.0 - (distance / isolation) ** 2)

    def fertility(self, organism: Organism) -> float:
        if not organism.reproduction.mature:
            return 0.0
        return SENESCENT_FERTILITY if self._mechanics.is_senescent(organism) else 1.0

    def attempt(self, mother: Organism, father: Organism, tick: int) -> Pregnancy | None:
        if mother.reproduction.pregnancy is not None:
            return None
        energy = min(1.0, self._mechanics.energy_fraction(mother))
        probability = (
            self.fertility(mother)
            * self.fertility(father)
            * mother.body.health
            * math.sqrt(energy)
            * self.compatibility(mother, father)
        )
        if self._rng.random() >= probability:
            return None
        phenotype = mother.phenotype
        litter_mass = phenotype.litter_mass_fraction * phenotype.adult_mass_kg
        return Pregnancy(
            father_id=father.id,
            father_genome=father.genome.copy(),
            conceived_tick=tick,
            due_tick=tick + max(1, round(phenotype.gestation_ticks)),
            litter_size=phenotype.litter_size,
            litter_mass_kg=litter_mass,
        )

    def pregnancy_cost(self, mother: Organism) -> float:
        pregnancy = mother.reproduction.pregnancy
        if pregnancy is None:
            return 0.0
        duration = max(1, pregnancy.due_tick - pregnancy.conceived_tick)
        reproduction = self._ecology.reproduction
        discount = self._ecology.life_history.construction_energy_discount
        return (
            reproduction.pregnancy_cost_multiplier
            * discount
            * self._ecology.metabolism.lean_energy_density_eu_per_kg
            * pregnancy.litter_mass_kg
            / duration
        )

    def miscarries(self, mother: Organism) -> bool:
        reproduction = self._ecology.reproduction
        starving = self._mechanics.energy_fraction(mother) < reproduction.miscarriage_energy_fraction
        return starving and self._rng.random() < reproduction.miscarriage_probability_per_tick

    def birth_complication(self, mother: Organism) -> bool:
        pregnancy = mother.reproduction.pregnancy
        if pregnancy is None:
            return False
        burden = pregnancy.litter_mass_kg / max(BURDEN_REFERENCE_MASS_FRACTION * mother.body.mass_kg, 1e-6)
        return self._rng.random() < self._ecology.reproduction.birth_complication_base * burden
