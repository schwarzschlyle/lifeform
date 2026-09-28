from __future__ import annotations

import math
from dataclasses import dataclass

DAY_PHASE_WORDS: tuple[str, ...] = (
    "midnight",
    "deep night",
    "before dawn",
    "dawn",
    "morning",
    "late morning",
    "midday",
    "afternoon",
    "late afternoon",
    "dusk",
    "evening",
    "night",
)

SEASON_STAGE_WORDS: tuple[str, ...] = ("early", "mid", "late")


@dataclass(frozen=True, slots=True)
class Calendar:
    ticks_per_day: int
    days_per_season: int
    season_names: tuple[str, ...]
    days_per_lunar_cycle: int
    hours_per_day: float = 24.0

    @property
    def ticks_per_season(self) -> int:
        return self.ticks_per_day * self.days_per_season

    @property
    def ticks_per_year(self) -> int:
        return self.ticks_per_season * len(self.season_names)

    @property
    def hours_per_tick(self) -> float:
        return self.hours_per_day / self.ticks_per_day

    def day_index(self, tick: int) -> int:
        return tick // self.ticks_per_day

    def tick_of_day(self, tick: int) -> int:
        return tick % self.ticks_per_day

    def hour_of_day(self, tick: int) -> float:
        return self.tick_of_day(tick) * self.hours_per_tick

    def day_phase_word(self, tick: int) -> str:
        phase_index = int(self.tick_of_day(tick) * len(DAY_PHASE_WORDS) / self.ticks_per_day)
        return DAY_PHASE_WORDS[phase_index]

    def season_index(self, tick: int) -> int:
        return (tick % self.ticks_per_year) // self.ticks_per_season

    def season_progress(self, tick: int) -> float:
        return (tick % self.ticks_per_season) / self.ticks_per_season

    def season_word(self, tick: int) -> str:
        name = self.season_names[self.season_index(tick)]
        if name.split(" ", 1)[0] in SEASON_STAGE_WORDS:
            return name
        stage = SEASON_STAGE_WORDS[min(int(self.season_progress(tick) * len(SEASON_STAGE_WORDS)), 2)]
        return f"{stage} {name}"

    def year_fraction(self, tick: int) -> float:
        return (tick % self.ticks_per_year) / self.ticks_per_year

    def lunar_brightness(self, tick: int) -> float:
        cycle_ticks = self.days_per_lunar_cycle * self.ticks_per_day
        return (1.0 - math.cos(2.0 * math.pi * (tick % cycle_ticks) / cycle_ticks)) / 2.0

    def days(self, tick_count: float) -> float:
        return tick_count / self.ticks_per_day
