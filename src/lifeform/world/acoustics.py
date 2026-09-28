from __future__ import annotations

import math
from dataclasses import dataclass

from lifeform.core.geometry import Position


@dataclass(frozen=True, slots=True)
class SoundEvent:
    source_id: int
    species_id: int
    position: Position
    kind: str
    level_db: float
    is_call: bool


class SoundBoard:
    def __init__(self) -> None:
        self._emitting: list[SoundEvent] = []
        self.audible: list[SoundEvent] = []

    def emit(self, event: SoundEvent) -> None:
        self._emitting.append(event)

    def rotate(self) -> None:
        self.audible = self._emitting
        self._emitting = []

    @property
    def emitted_this_tick(self) -> list[SoundEvent]:
        return list(self._emitting)


def received_level_db(source_db: float, distance: float, attenuation_per_patch_db: float) -> float:
    return source_db - 20.0 * math.log10(max(distance, 1.0)) - attenuation_per_patch_db * distance
