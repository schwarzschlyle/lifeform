from __future__ import annotations

from dataclasses import dataclass, field
from enum import IntEnum

import numpy as np
import numpy.typing as npt

IMPASSABLE = float("inf")
DEEP_WATER_DEPTH_M = 3.0
SHALLOW_WATER_DEPTH_M = 0.5
RIVER_DEPTH_M = 0.4


class TerrainType(IntEnum):
    DEEP_WATER = 0
    SHALLOW_WATER = 1
    BEACH = 2
    GRASSLAND = 3
    SAVANNA = 4
    FOREST = 5
    RAINFOREST = 6
    WETLAND = 7
    DESERT = 8
    TUNDRA = 9
    ROCK = 10
    VOLCANIC = 11
    CAVE = 12


class FoodLayer(IntEnum):
    GRASS = 0
    BROWSE = 1
    FRUIT = 2
    SEEDS = 3
    INVERTEBRATES = 4
    ALGAE = 5
    FUNGI = 6

    @property
    def key(self) -> str:
        return self.name.lower()


@dataclass(frozen=True, slots=True)
class TerrainProperties:
    terrain: TerrainType
    description: str
    move_cost: float
    swim_required: bool
    cover: float
    sight_opacity: float
    diurnal_damping: float
    temperature_offset_c: float
    canopy_max: float
    diggable: bool
    capacity_kg: dict[FoodLayer, float] = field(default_factory=dict)


_CATALOG: tuple[TerrainProperties, ...] = (
    TerrainProperties(
        TerrainType.DEEP_WATER, "deep water", IMPASSABLE, True, 0.1, 0.0, 0.8, 0.0, 0.0, False, {FoodLayer.ALGAE: 2.0}
    ),
    TerrainProperties(
        TerrainType.SHALLOW_WATER,
        "shallow water",
        2.0,
        False,
        0.2,
        0.0,
        0.6,
        0.0,
        0.0,
        False,
        {FoodLayer.ALGAE: 3.0, FoodLayer.INVERTEBRATES: 2.0},
    ),
    TerrainProperties(
        TerrainType.BEACH,
        "sandy shore",
        1.3,
        False,
        0.0,
        0.0,
        0.2,
        0.0,
        0.0,
        True,
        {FoodLayer.INVERTEBRATES: 1.0, FoodLayer.SEEDS: 0.5},
    ),
    TerrainProperties(
        TerrainType.GRASSLAND,
        "open grassland",
        1.0,
        False,
        0.1,
        0.02,
        0.0,
        0.0,
        0.05,
        True,
        {FoodLayer.GRASS: 8.0, FoodLayer.SEEDS: 2.0, FoodLayer.INVERTEBRATES: 1.0},
    ),
    TerrainProperties(
        TerrainType.SAVANNA,
        "savanna with scattered trees",
        1.1,
        False,
        0.25,
        0.05,
        0.1,
        0.0,
        0.2,
        True,
        {FoodLayer.GRASS: 6.0, FoodLayer.BROWSE: 3.0, FoodLayer.SEEDS: 2.0},
    ),
    TerrainProperties(
        TerrainType.FOREST,
        "forest",
        1.4,
        False,
        0.5,
        0.2,
        0.4,
        -1.0,
        0.8,
        True,
        {FoodLayer.BROWSE: 6.0, FoodLayer.FRUIT: 3.0, FoodLayer.INVERTEBRATES: 3.0, FoodLayer.FUNGI: 1.0},
    ),
    TerrainProperties(
        TerrainType.RAINFOREST,
        "dense rainforest",
        1.7,
        False,
        0.8,
        0.35,
        0.6,
        -1.0,
        0.95,
        True,
        {FoodLayer.FRUIT: 8.0, FoodLayer.BROWSE: 5.0, FoodLayer.INVERTEBRATES: 5.0, FoodLayer.FUNGI: 2.0},
    ),
    TerrainProperties(
        TerrainType.WETLAND,
        "marsh",
        1.6,
        False,
        0.4,
        0.1,
        0.5,
        0.0,
        0.1,
        False,
        {FoodLayer.GRASS: 5.0, FoodLayer.ALGAE: 3.0, FoodLayer.INVERTEBRATES: 4.0},
    ),
    TerrainProperties(
        TerrainType.DESERT,
        "desert",
        1.2,
        False,
        0.05,
        0.0,
        -0.3,
        2.0,
        0.0,
        True,
        {FoodLayer.SEEDS: 1.5, FoodLayer.INVERTEBRATES: 0.5},
    ),
    TerrainProperties(
        TerrainType.TUNDRA,
        "tundra",
        1.5,
        False,
        0.05,
        0.0,
        0.1,
        0.0,
        0.0,
        True,
        {FoodLayer.GRASS: 2.0, FoodLayer.INVERTEBRATES: 0.3},
    ),
    TerrainProperties(
        TerrainType.ROCK,
        "rocky ground",
        2.2,
        False,
        0.4,
        0.6,
        0.2,
        0.0,
        0.0,
        False,
        {FoodLayer.SEEDS: 0.5, FoodLayer.GRASS: 1.0},
    ),
    TerrainProperties(
        TerrainType.VOLCANIC, "volcanic ground", 1.3, False, 0.2, 0.05, 0.3, 8.0, 0.0, False, {FoodLayer.FUNGI: 1.0}
    ),
    TerrainProperties(
        TerrainType.CAVE,
        "cave",
        1.5,
        False,
        0.9,
        0.9,
        0.95,
        0.0,
        0.0,
        False,
        {FoodLayer.FUNGI: 4.0, FoodLayer.INVERTEBRATES: 3.0},
    ),
)


class TerrainCatalog:
    def __init__(self) -> None:
        self._by_type = {properties.terrain: properties for properties in _CATALOG}
        self.move_cost = self._column("move_cost")
        self.cover = self._column("cover")
        self.sight_opacity = self._column("sight_opacity")
        self.diurnal_damping = self._column("diurnal_damping")
        self.temperature_offset = self._column("temperature_offset_c")
        self.canopy_max = self._column("canopy_max")
        self.capacity = np.array(
            [[properties.capacity_kg.get(layer, 0.0) for layer in FoodLayer] for properties in _CATALOG],
            dtype=np.float32,
        )

    def __getitem__(self, terrain: int) -> TerrainProperties:
        return self._by_type[TerrainType(terrain)]

    def description(self, terrain: int) -> str:
        return self[terrain].description

    def is_water(self, terrain: int) -> bool:
        return terrain in (TerrainType.DEEP_WATER, TerrainType.SHALLOW_WATER)

    @staticmethod
    def _column(attribute: str) -> npt.NDArray[np.float32]:
        return np.array([getattr(properties, attribute) for properties in _CATALOG], dtype=np.float32)


TERRAIN = TerrainCatalog()
