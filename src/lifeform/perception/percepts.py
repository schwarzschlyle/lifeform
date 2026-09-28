from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from lifeform.core.geometry import Direction, Position
from lifeform.world.acoustics import SoundEvent


class EntityKind(StrEnum):
    ANIMAL = "animal"
    CARCASS = "carcass"


@dataclass(slots=True)
class EntityPercept:
    kind: EntityKind
    target_id: int
    position: Position
    distance: float
    direction: Direction
    certainty: float
    touching: bool
    moving: bool
    salience: float = 0.0
    danger: float = 0.0
    label: str = ""


@dataclass(slots=True)
class ScentPercept:
    channel: str
    intensity: float
    direction: Direction | None
    upwind: bool
    species_id: int | None
    salience: float = 0.0
    label: str = ""


@dataclass(slots=True)
class SoundPercept:
    event: SoundEvent
    loudness_db: float
    direction: Direction
    distance: float
    salience: float = 0.0
    label: str = ""


@dataclass(slots=True)
class PerceptualField:
    entities: list[EntityPercept]
    scents: list[ScentPercept]
    sounds: list[SoundPercept]

    def entity(self, label: str) -> EntityPercept | None:
        for percept in self.entities:
            if percept.label == label:
                return percept
        return None

    def animal_ids(self) -> set[int]:
        return {percept.target_id for percept in self.entities if percept.kind == EntityKind.ANIMAL}
