from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum

import numpy as np

from lifeform.biology.genome import AlleleArray
from lifeform.core.identifiers import IdSequence


class InfectionStage(StrEnum):
    SUSCEPTIBLE = "susceptible"
    EXPOSED = "exposed"
    INFECTIOUS = "infectious"
    RECOVERED = "recovered"


@dataclass(frozen=True, slots=True)
class Strain:
    strain_id: int
    parent_id: int | None
    transmission: float
    virulence: float
    latent_ticks: float
    infectious_ticks: float
    immunity_ticks: float
    environmental_shedding: float
    environmental_half_life_ticks: float
    host_genotype: AlleleArray
    host_distance: float


@dataclass(slots=True)
class InfectionState:
    stage: InfectionStage = InfectionStage.SUSCEPTIBLE
    strain_id: int | None = None
    stage_ticks_left: int = 0
    immunity_ticks_left: int = 0
    immune_to: set[int] = field(default_factory=set)

    @property
    def infectious(self) -> bool:
        return self.stage == InfectionStage.INFECTIOUS

    @property
    def infected(self) -> bool:
        return self.stage in (InfectionStage.EXPOSED, InfectionStage.INFECTIOUS)


class StrainRegistry:
    def __init__(self) -> None:
        self._ids = IdSequence()
        self.strains: dict[int, Strain] = {}

    def register(
        self,
        transmission: float,
        virulence: float,
        latent_ticks: float,
        infectious_ticks: float,
        immunity_ticks: float,
        shedding: float,
        half_life_ticks: float,
        host_genotype: AlleleArray,
        host_distance: float,
        parent_id: int | None = None,
    ) -> Strain:
        strain = Strain(
            self._ids.next(),
            parent_id,
            transmission,
            virulence,
            latent_ticks,
            infectious_ticks,
            immunity_ticks,
            shedding,
            half_life_ticks,
            host_genotype.copy(),
            host_distance,
        )
        self.strains[strain.strain_id] = strain
        return strain

    def mutate(
        self, parent: Strain, rng: np.random.Generator, sigma: float, ceiling: float, half_saturation: float
    ) -> Strain:
        virulence = float(parent.virulence * np.exp(rng.normal(0.0, sigma)))
        transmission = ceiling * virulence / (virulence + half_saturation)
        return self.register(
            transmission,
            virulence,
            parent.latent_ticks,
            parent.infectious_ticks,
            parent.immunity_ticks,
            parent.environmental_shedding,
            parent.environmental_half_life_ticks,
            parent.host_genotype,
            parent.host_distance,
            parent.strain_id,
        )
