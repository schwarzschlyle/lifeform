from __future__ import annotations

import math
from dataclasses import dataclass

from lifeform.core.geometry import Position, TorusMetric
from lifeform.core.identifiers import IdSequence

MARK_FADE_THRESHOLD = 0.05
CACHE_EMPTY_KG = 1e-4


@dataclass(slots=True)
class Carcass:
    carcass_id: int
    position: Position
    mass_kg: float
    initial_mass_kg: float
    species_id: int
    origin_id: int
    toxicity: float
    strain_id: int | None
    age_ticks: int = 0
    spoilage: float = 0.0

    @property
    def remaining_fraction(self) -> float:
        return self.mass_kg / max(self.initial_mass_kg, 1e-9)


@dataclass(slots=True)
class Den:
    den_id: int
    owner_id: int
    position: Position
    quality: float = 1.0


@dataclass(slots=True)
class DenProject:
    owner_id: int
    position: Position
    work_ticks: int = 0


@dataclass(slots=True)
class TerritoryMark:
    owner_id: int
    species_id: int
    position: Position
    strength: float = 1.0


@dataclass(slots=True)
class FoodCache:
    owner_id: int
    position: Position
    layer_key: str
    mass_kg: float


class CarcassRegistry:
    def __init__(self, metric: TorusMetric) -> None:
        self._metric = metric
        self._ids = IdSequence()
        self.items: dict[int, Carcass] = {}

    def create(
        self,
        position: Position,
        mass_kg: float,
        species_id: int,
        origin_id: int,
        toxicity: float,
        strain_id: int | None,
    ) -> Carcass:
        carcass = Carcass(self._ids.next(), position, mass_kg, mass_kg, species_id, origin_id, toxicity, strain_id)
        self.items[carcass.carcass_id] = carcass
        return carcass

    def near(self, position: Position, radius: float) -> list[Carcass]:
        return [
            carcass for carcass in self.items.values() if self._metric.distance(position, carcass.position) <= radius
        ]

    def at_or_adjacent(self, position: Position) -> list[Carcass]:
        return [carcass for carcass in self.items.values() if self._metric.are_adjacent(position, carcass.position)]

    def remove(self, carcass_id: int) -> None:
        self.items.pop(carcass_id, None)


class DenRegistry:
    def __init__(self) -> None:
        self._ids = IdSequence()
        self.items: dict[int, Den] = {}
        self.projects: dict[int, DenProject] = {}

    def at(self, position: Position) -> Den | None:
        for den in self.items.values():
            if den.position == position:
                return den
        return None

    def owned_by(self, owner_id: int) -> Den | None:
        for den in self.items.values():
            if den.owner_id == owner_id:
                return den
        return None

    def advance_project(self, owner_id: int, position: Position, required_ticks: int) -> Den | None:
        project = self.projects.get(owner_id)
        if project is None or project.position != position:
            project = DenProject(owner_id, position)
            self.projects[owner_id] = project
        project.work_ticks += 1
        if project.work_ticks < required_ticks:
            return None
        del self.projects[owner_id]
        existing = self.owned_by(owner_id)
        if existing is not None:
            del self.items[existing.den_id]
        den = Den(self._ids.next(), owner_id, position)
        self.items[den.den_id] = den
        return den

    def release_owner(self, owner_id: int) -> None:
        self.projects.pop(owner_id, None)


class TerritoryMarks:
    def __init__(self, metric: TorusMetric, half_life_ticks: float) -> None:
        self._metric = metric
        self._decay = math.log(2.0) / half_life_ticks
        self.items: list[TerritoryMark] = []

    def place(self, owner_id: int, species_id: int, position: Position) -> None:
        self.items.append(TerritoryMark(owner_id, species_id, position))

    def near(self, position: Position, radius: float) -> list[TerritoryMark]:
        return [mark for mark in self.items if self._metric.distance(position, mark.position) <= radius]

    def decay(self) -> None:
        for mark in self.items:
            mark.strength *= math.exp(-self._decay)
        self.items = [mark for mark in self.items if mark.strength > MARK_FADE_THRESHOLD]


class FoodCaches:
    def __init__(self) -> None:
        self.items: list[FoodCache] = []

    def store(self, owner_id: int, position: Position, layer_key: str, mass_kg: float) -> None:
        for cache in self.items:
            if cache.owner_id == owner_id and cache.position == position and cache.layer_key == layer_key:
                cache.mass_kg += mass_kg
                return
        self.items.append(FoodCache(owner_id, position, layer_key, mass_kg))

    def at(self, position: Position) -> list[FoodCache]:
        return [cache for cache in self.items if cache.position == position and cache.mass_kg > 0.0]

    def prune(self) -> None:
        self.items = [cache for cache in self.items if cache.mass_kg > CACHE_EMPTY_KG]
