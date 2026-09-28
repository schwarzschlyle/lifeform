from __future__ import annotations

import numpy as np

from lifeform.biology.disease import InfectionStage, Strain, StrainRegistry
from lifeform.biology.genome import genotype_distance
from lifeform.biology.organism import Organism
from lifeform.config.parameters import DiseaseParameters
from lifeform.world.world import World

MIN_STAGE_TICKS = 1


class TransmissionModel:
    def __init__(self, parameters: DiseaseParameters, strains: StrainRegistry, rng: np.random.Generator) -> None:
        self._parameters = parameters
        self.strains = strains
        self._rng = rng

    def susceptibility(self, organism: Organism) -> float:
        parameters = self._parameters
        return (1.0 - parameters.susceptibility_immune_reduction * organism.trait("immune_investment")) * (
            1.0 + parameters.stress_susceptibility * organism.body.stress
        )

    def can_host(self, organism: Organism, strain: Strain) -> bool:
        return genotype_distance(organism.genome.genotype, strain.host_genotype) <= strain.host_distance

    def infect(self, organism: Organism, strain: Strain) -> bool:
        infection = organism.infection
        if infection.stage != InfectionStage.SUSCEPTIBLE or strain.strain_id in infection.immune_to:
            return False
        if not self.can_host(organism, strain):
            return False
        infection.stage = InfectionStage.EXPOSED
        infection.strain_id = strain.strain_id
        infection.stage_ticks_left = self._duration(strain.latent_ticks)
        return True

    def contact(self, carrier: Organism, contact: Organism) -> Strain | None:
        strain_id = carrier.infection.strain_id
        if strain_id is None or not carrier.infection.infectious:
            return None
        strain = self.strains.strains[strain_id]
        if self._rng.random() >= strain.transmission * self.susceptibility(contact):
            return None
        transmitted = self._maybe_mutated(strain)
        return transmitted if self.infect(contact, transmitted) else None

    def environmental_exposure(self, organism: Organism, world: World) -> Strain | None:
        position = organism.position
        for strain_id, grid in world.fields.pathogen.load.items():
            load = float(grid[position.y, position.x])
            if load <= 0.0 or strain_id not in self.strains.strains:
                continue
            chance = self._parameters.environment_transmission * load * self.susceptibility(organism)
            if self._rng.random() < chance:
                strain = self.strains.strains[strain_id]
                return strain if self.infect(organism, strain) else None
        return None

    def progress(self, organism: Organism, world: World) -> float:
        infection = organism.infection
        if infection.stage == InfectionStage.RECOVERED:
            infection.immunity_ticks_left -= 1
            if infection.immunity_ticks_left <= 0:
                infection.stage = InfectionStage.SUSCEPTIBLE
            return 0.0
        if infection.strain_id is None or not infection.infected:
            return 0.0
        strain = self.strains.strains[infection.strain_id]
        infection.stage_ticks_left -= 1
        if infection.stage == InfectionStage.EXPOSED:
            if infection.stage_ticks_left <= 0:
                infection.stage = InfectionStage.INFECTIOUS
                infection.stage_ticks_left = self._duration(strain.infectious_ticks)
            return 0.0
        organism.body.take_damage("disease", strain.virulence, world.tick)
        position = organism.position
        world.fields.pathogen.shed(
            strain.strain_id,
            position.x,
            position.y,
            strain.environmental_shedding,
            strain.environmental_half_life_ticks,
        )
        recovery = (1.0 / max(strain.infectious_ticks, 1.0)) * (1.0 + organism.trait("immune_investment"))
        if infection.stage_ticks_left <= 0 or self._rng.random() < recovery:
            infection.stage = InfectionStage.RECOVERED
            infection.immune_to.add(strain.strain_id)
            infection.immunity_ticks_left = self._duration(strain.immunity_ticks)
            infection.strain_id = None
        return strain.virulence

    def _duration(self, mean_ticks: float) -> int:
        return max(MIN_STAGE_TICKS, int(self._rng.geometric(1.0 / max(mean_ticks, 1.0))))

    def _maybe_mutated(self, strain: Strain) -> Strain:
        parameters = self._parameters
        if self._rng.random() >= parameters.strain_mutation_probability:
            return strain
        return self.strains.mutate(
            strain,
            self._rng,
            parameters.virulence_mutation_sigma,
            parameters.transmission_ceiling,
            parameters.virulence_half_saturation,
        )
