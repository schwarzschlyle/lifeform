from __future__ import annotations

import numpy as np

from lifeform.biology import allometry
from lifeform.biology.organism import Organism
from lifeform.biology.social import EloDominance
from lifeform.config.parameters import SocialParameters

WEAPON_BASE = 0.5
ORNAMENT_WEIGHT = 0.2
RHP_NOISE = 0.15


class ContestModel:
    def __init__(self, parameters: SocialParameters, rng: np.random.Generator) -> None:
        self._parameters = parameters
        self._rng = rng
        self._elo = EloDominance(parameters.elo_k_factor)

    def holding_potential(self, organism: Organism) -> float:
        noise = float(self._rng.normal(1.0, RHP_NOISE))
        return (
            allometry.muscle_scale(organism.body.mass_kg)
            * (WEAPON_BASE + organism.trait("weaponry"))
            * organism.body.health
            * (1.0 + ORNAMENT_WEIGHT * organism.trait("ornament"))
            * noise
        )

    def display_contest(self, first: Organism, second: Organism) -> tuple[Organism, Organism]:
        if self.holding_potential(first) >= self.holding_potential(second):
            return first, second
        return second, first

    def settle(self, winner: Organism, loser: Organism, tick: int) -> None:
        self._elo.settle(winner.social, loser.social)
        loser.social.defeated_until_tick = tick + self._parameters.defeat_memory_ticks
        loser.social.last_defeated_by = winner.id

    @staticmethod
    def priority(organism: Organism) -> float:
        return EloDominance.priority_weight(organism.social.rating) * allometry.kleiber(organism.body.mass_kg, 1.0)
