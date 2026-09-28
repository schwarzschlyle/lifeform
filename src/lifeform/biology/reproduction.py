from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum

from lifeform.biology.genome import Genome


class Sex(StrEnum):
    FEMALE = "female"
    MALE = "male"


@dataclass(slots=True)
class Pregnancy:
    father_id: int
    father_genome: Genome
    conceived_tick: int
    due_tick: int
    litter_size: int
    litter_mass_kg: float

    def progress(self, tick: int) -> float:
        return (tick - self.conceived_tick) / max(1, self.due_tick - self.conceived_tick)


@dataclass(slots=True)
class ReproductiveState:
    sex: Sex
    estrus_offset: int
    mature: bool = False
    weaned: bool = False
    pregnancy: Pregnancy | None = None
    lactating: bool = False
    dependents: set[int] = field(default_factory=set)
    courted_by: dict[int, int] = field(default_factory=dict)
    courting: dict[int, int] = field(default_factory=dict)
    mother_id: int | None = None
    offspring_count: int = 0

    @property
    def is_female(self) -> bool:
        return self.sex == Sex.FEMALE

    def forget_old_courtship(self, tick: int, memory_ticks: int) -> None:
        self.courted_by = {suitor: when for suitor, when in self.courted_by.items() if tick - when <= memory_ticks}
        self.courting = {target: when for target, when in self.courting.items() if tick - when <= memory_ticks}
