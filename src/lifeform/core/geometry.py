from __future__ import annotations

import math
from dataclasses import dataclass
from enum import IntEnum


class Direction(IntEnum):
    NORTH = 0
    NORTH_EAST = 1
    EAST = 2
    SOUTH_EAST = 3
    SOUTH = 4
    SOUTH_WEST = 5
    WEST = 6
    NORTH_WEST = 7

    @property
    def offset(self) -> tuple[int, int]:
        return _OFFSETS[self]

    @property
    def word(self) -> str:
        return self.name.lower().replace("_", "-")

    @property
    def key(self) -> str:
        return self.name.lower().replace("_", "")

    @property
    def opposite(self) -> Direction:
        return Direction((self.value + 4) % 8)

    @property
    def is_diagonal(self) -> bool:
        return self.value % 2 == 1

    @classmethod
    def from_offset(cls, dx: float, dy: float) -> Direction:
        angle_from_north = math.atan2(dx, -dy)
        sector = round(angle_from_north / (math.pi / 4)) % 8
        return cls(sector)


_OFFSETS: dict[Direction, tuple[int, int]] = {
    Direction.NORTH: (0, -1),
    Direction.NORTH_EAST: (1, -1),
    Direction.EAST: (1, 0),
    Direction.SOUTH_EAST: (1, 1),
    Direction.SOUTH: (0, 1),
    Direction.SOUTH_WEST: (-1, 1),
    Direction.WEST: (-1, 0),
    Direction.NORTH_WEST: (-1, -1),
}


@dataclass(frozen=True, slots=True)
class Position:
    x: int
    y: int


class TorusMetric:
    def __init__(self, width: int, height: int) -> None:
        self.width = width
        self.height = height

    def wrap(self, x: int, y: int) -> Position:
        return Position(x % self.width, y % self.height)

    def delta(self, origin: Position, target: Position) -> tuple[int, int]:
        return self._shortest(target.x - origin.x, self.width), self._shortest(target.y - origin.y, self.height)

    def distance(self, origin: Position, target: Position) -> float:
        dx, dy = self.delta(origin, target)
        return math.hypot(dx, dy)

    def steps(self, origin: Position, target: Position) -> int:
        dx, dy = self.delta(origin, target)
        return max(abs(dx), abs(dy))

    def direction(self, origin: Position, target: Position) -> Direction:
        dx, dy = self.delta(origin, target)
        return Direction.from_offset(dx, dy)

    def step(self, position: Position, direction: Direction) -> Position:
        dx, dy = direction.offset
        return self.wrap(position.x + dx, position.y + dy)

    def neighbors(self, position: Position) -> list[Position]:
        return [self.step(position, direction) for direction in Direction]

    def are_adjacent(self, first: Position, second: Position) -> bool:
        return self.steps(first, second) <= 1

    @staticmethod
    def _shortest(difference: int, extent: int) -> int:
        half = extent // 2
        return (difference + half) % extent - half
