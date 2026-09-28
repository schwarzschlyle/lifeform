from __future__ import annotations

import math
from dataclasses import dataclass, field

ELO_SCALE = 400.0
BOND_FORGET_THRESHOLD = 0.02


@dataclass(slots=True)
class SocialState:
    rating: float
    bonds: dict[int, float] = field(default_factory=dict)
    defeated_until_tick: int = -1
    last_defeated_by: int | None = None

    def strengthen_bond(self, other_id: int, amount: float) -> None:
        self.bonds[other_id] = min(1.0, self.bonds.get(other_id, 0.0) + amount)

    def decay_bonds(self, half_life_ticks: float) -> None:
        retention = math.exp(-math.log(2.0) / half_life_ticks)
        self.bonds = {
            other: strength * retention for other, strength in self.bonds.items() if strength > BOND_FORGET_THRESHOLD
        }


class EloDominance:
    def __init__(self, k_factor: float) -> None:
        self._k_factor = k_factor

    @staticmethod
    def expected_score(rating: float, opponent_rating: float) -> float:
        return 1.0 / (1.0 + math.pow(10.0, (opponent_rating - rating) / ELO_SCALE))

    def settle(self, winner: SocialState, loser: SocialState) -> None:
        expected = self.expected_score(winner.rating, loser.rating)
        shift = self._k_factor * (1.0 - expected)
        winner.rating += shift
        loser.rating -= shift

    @staticmethod
    def priority_weight(rating: float) -> float:
        return math.pow(10.0, rating / ELO_SCALE)
