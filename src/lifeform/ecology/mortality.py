from __future__ import annotations

import math
from enum import StrEnum

import numpy as np

from lifeform.biology.mechanics import BodyMechanics
from lifeform.biology.organism import Organism
from lifeform.config.parameters import EcologyParameters
from lifeform.world.terrain import TerrainType
from lifeform.world.world import World

DROWNING_PROBABILITY = 0.5
TOXIN_LETHAL_BASE = 1.0
TOXIN_RESISTANCE_TOLERANCE = 2.0


class DeathCause(StrEnum):
    STARVATION = "starvation"
    DEHYDRATION = "dehydration"
    PREDATION = "predation"
    COMBAT = "combat"
    DISEASE = "disease"
    SENESCENCE = "senescence"
    HYPOTHERMIA = "hypothermia"
    HYPERTHERMIA = "hyperthermia"
    TOXIN = "toxin"
    DROWNING = "drowning"
    FIRE = "fire"
    DISASTER = "disaster"
    BIRTH_COMPLICATIONS = "birth_complications"


DAMAGE_SOURCES: dict[str, DeathCause] = {
    "starvation": DeathCause.STARVATION,
    "dehydration": DeathCause.DEHYDRATION,
    "predation": DeathCause.PREDATION,
    "combat": DeathCause.COMBAT,
    "retaliation": DeathCause.COMBAT,
    "disease": DeathCause.DISEASE,
    "hypothermia": DeathCause.HYPOTHERMIA,
    "hyperthermia": DeathCause.HYPERTHERMIA,
    "toxin": DeathCause.TOXIN,
    "fire": DeathCause.FIRE,
    "disaster": DeathCause.DISASTER,
    "drowning": DeathCause.DROWNING,
    "birth_complications": DeathCause.BIRTH_COMPLICATIONS,
}


class MortalityJudge:
    def __init__(self, ecology: EcologyParameters, mechanics: BodyMechanics, rng: np.random.Generator) -> None:
        self._ecology = ecology
        self._mechanics = mechanics
        self._rng = rng

    def judge(self, organism: Organism, world: World) -> DeathCause | None:
        body = organism.body
        if body.health <= 0.0:
            return self._cause_of_injury(organism)
        if body.dry_ticks >= self._ecology.water.lethal_dry_ticks:
            return DeathCause.DEHYDRATION
        if body.mass_kg < self._ecology.metabolism.lethal_lean_mass_fraction * body.lean_mass_kg:
            return DeathCause.STARVATION
        lethal_toxin = TOXIN_LETHAL_BASE * (1.0 + TOXIN_RESISTANCE_TOLERANCE * organism.trait("toxin_resistance"))
        if body.toxin_load >= lethal_toxin:
            return DeathCause.TOXIN
        if self._drowns(organism, world):
            return DeathCause.DROWNING
        if self._rng.random() < self.senescence_probability(organism):
            return DeathCause.SENESCENCE
        return None

    def senescence_probability(self, organism: Organism) -> float:
        aging = self._ecology.aging
        relative_age = organism.body.age_ticks / max(organism.phenotype.lifespan_ticks, 1.0)
        hazard = aging.background_hazard_per_tick + aging.gompertz_scale * math.exp(aging.gompertz_rate * relative_age)
        return 1.0 - math.exp(-hazard)

    def _drowns(self, organism: Organism, world: World) -> bool:
        in_deep_water = world.terrain_at(organism.position) == TerrainType.DEEP_WATER
        if not in_deep_water or organism.body.climbing or self._mechanics.can_swim_deep(organism):
            return False
        organism.body.take_damage("drowning", 0.0, world.tick)
        return self._rng.random() < DROWNING_PROBABILITY

    @staticmethod
    def _cause_of_injury(organism: Organism) -> DeathCause:
        source = organism.body.damage.dominant_source()
        if source is None:
            return DeathCause.STARVATION
        return DAMAGE_SOURCES.get(source, DeathCause.COMBAT)
