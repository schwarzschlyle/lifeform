from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np

from lifeform.config.world_preset import FeatureStamp, WorldPreset
from lifeform.world.field_math import FloatGrid
from lifeform.world.generation.blueprint import WorldBlueprint
from lifeform.world.generation.noise import PeriodicNoise, normalized
from lifeform.world.terrain import DEEP_WATER_DEPTH_M, RIVER_DEPTH_M, SHALLOW_WATER_DEPTH_M, TERRAIN, TerrainType
from lifeform.world.thermal_baseline import ThermalBaseline

MOISTURE_VARIATION = 0.15
HIGHLAND_DRYING = 0.15
WETLAND_MOISTURE = 0.8
WETLAND_ELEVATION_MARGIN = 0.04
CAVE_FILL_PROBABILITY = 0.45
CAVE_SMOOTHING_PASSES = 5
RIFT_WAVINESS_PATCHES = 4.0


class ElevationBuilder:
    def __init__(self, noise: PeriodicNoise) -> None:
        self._noise = noise

    def build(self, preset: WorldPreset) -> FloatGrid:
        terrain = preset.terrain
        base = self._noise.fractal(terrain.lattice_cells, terrain.octaves, terrain.persistence)
        ridged = 1.0 - np.abs(2.0 * self._noise.fractal(terrain.lattice_cells, terrain.octaves, 0.55) - 1.0)
        mountains = np.clip(self._noise.fractal(max(2, terrain.lattice_cells // 2), 3, 0.5) - 0.5, 0.0, None) * 2.0
        blended = (1.0 - terrain.ridge_strength) * base + terrain.ridge_strength * ridged
        return normalized(blended + terrain.mountain_strength * mountains)


class WaterBuilder:
    def __init__(self, preset: WorldPreset) -> None:
        self._preset = preset

    def sea_level(self, elevation: FloatGrid) -> float:
        if self._preset.terrain.water_fraction <= 0.0:
            return -1.0
        return float(np.quantile(elevation, self._preset.terrain.water_fraction))

    def river_mask(self, elevation: FloatGrid, sea: np.ndarray) -> np.ndarray:
        height, width = elevation.shape
        accumulation = np.ones(elevation.shape, dtype=np.float32)
        order = np.argsort(-elevation, axis=None)
        for flat_index in order:
            row, column = divmod(int(flat_index), width)
            if sea[row, column]:
                continue
            target = self._lowest_neighbor(elevation, row, column, height, width)
            if target is not None:
                accumulation[target] += accumulation[row, column]
        threshold = self._preset.terrain.river_threshold_fraction * elevation.size
        return (accumulation >= threshold) & ~sea

    @staticmethod
    def _lowest_neighbor(
        elevation: FloatGrid, row: int, column: int, height: int, width: int
    ) -> tuple[int, int] | None:
        lowest = float(elevation[row, column])
        target: tuple[int, int] | None = None
        for row_step in (-1, 0, 1):
            for column_step in (-1, 0, 1):
                neighbor = ((row + row_step) % height, (column + column_step) % width)
                if float(elevation[neighbor]) < lowest:
                    lowest = float(elevation[neighbor])
                    target = neighbor
        return target


def distance_to(mask: np.ndarray, reach: int) -> FloatGrid:
    distance = np.full(mask.shape, float(reach), dtype=np.float32)
    frontier = mask.copy()
    distance[frontier] = 0.0
    for step in range(1, reach):
        grown = frontier.copy()
        for row_step, column_step in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            grown |= np.roll(frontier, (row_step, column_step), axis=(0, 1))
        fresh = grown & ~frontier
        distance[fresh] = float(step)
        frontier = grown
    return distance


def disc(shape: tuple[int, int], row: int, column: int, radius: float) -> np.ndarray:
    height, width = shape
    rows = (np.arange(height) - row + height // 2) % height - height // 2
    columns = (np.arange(width) - column + width // 2) % width - width // 2
    return (rows[:, None] ** 2 + columns[None, :] ** 2) <= radius**2


@dataclass(frozen=True, slots=True)
class BiomeRule:
    terrain: TerrainType
    min_temperature_c: float
    max_temperature_c: float
    min_moisture: float
    max_moisture: float

    def matches(self, temperature: FloatGrid, moisture: FloatGrid) -> np.ndarray:
        return (
            (temperature >= self.min_temperature_c)
            & (temperature < self.max_temperature_c)
            & (moisture >= self.min_moisture)
            & (moisture < self.max_moisture)
        )


WHITTAKER_RULES: tuple[BiomeRule, ...] = (
    BiomeRule(TerrainType.TUNDRA, -99.0, 0.0, 0.0, 2.0),
    BiomeRule(TerrainType.FOREST, -4.0, 6.0, 0.45, 2.0),
    BiomeRule(TerrainType.FOREST, 6.0, 19.0, 0.6, 2.0),
    BiomeRule(TerrainType.SAVANNA, 6.0, 19.0, 0.2, 0.35),
    BiomeRule(TerrainType.SAVANNA, 19.0, 99.0, 0.2, 0.5),
    BiomeRule(TerrainType.RAINFOREST, 19.0, 99.0, 0.68, 2.0),
    BiomeRule(TerrainType.DESERT, -99.0, 99.0, 0.0, 0.2),
)


class BiomeClassifier:
    def classify(
        self,
        elevation: FloatGrid,
        sea_level: float,
        deep_threshold: float,
        rock_threshold: float,
        temperature: FloatGrid,
        moisture: FloatGrid,
    ) -> np.ndarray:
        terrain = np.full(elevation.shape, TerrainType.GRASSLAND, dtype=np.uint8)
        for rule in WHITTAKER_RULES:
            terrain[rule.matches(temperature, moisture)] = rule.terrain
        lowland = elevation < sea_level + WETLAND_ELEVATION_MARGIN
        terrain[(moisture > WETLAND_MOISTURE) & lowland] = TerrainType.WETLAND
        terrain[elevation >= rock_threshold] = TerrainType.ROCK
        terrain[elevation < sea_level] = TerrainType.SHALLOW_WATER
        terrain[elevation < sea_level - deep_threshold] = TerrainType.DEEP_WATER
        return terrain


class FeatureStamper:
    def __init__(self, rng: np.random.Generator) -> None:
        self._rng = rng

    def apply(self, stamp: FeatureStamp, blueprint: WorldBlueprint) -> None:
        for _ in range(stamp.count):
            row, column = self._land_site(blueprint)
            radius = int(self._rng.integers(stamp.min_radius, stamp.max_radius + 1))
            getattr(self, f"_stamp_{stamp.kind}")(blueprint, row, column, radius)

    def _land_site(self, blueprint: WorldBlueprint) -> tuple[int, int]:
        water = np.isin(blueprint.terrain, (TerrainType.DEEP_WATER, TerrainType.SHALLOW_WATER))
        candidates = np.argwhere(~water)
        if len(candidates) == 0:
            candidates = np.argwhere(np.ones(blueprint.shape, dtype=bool))
        row, column = candidates[int(self._rng.integers(len(candidates)))]
        return int(row), int(column)

    def _stamp_waterholes(self, blueprint: WorldBlueprint, row: int, column: int, radius: int) -> None:
        pool = disc(blueprint.shape, row, column, radius)
        blueprint.terrain[pool] = TerrainType.SHALLOW_WATER
        blueprint.base_water[pool] = SHALLOW_WATER_DEPTH_M
        blueprint.moisture[disc(blueprint.shape, row, column, radius * 3)] = np.maximum(
            blueprint.moisture[disc(blueprint.shape, row, column, radius * 3)], 0.6
        )

    def _stamp_oases(self, blueprint: WorldBlueprint, row: int, column: int, radius: int) -> None:
        grove = disc(blueprint.shape, row, column, radius + 3) & ~disc(blueprint.shape, row, column, radius)
        blueprint.terrain[grove] = TerrainType.FOREST
        blueprint.canopy[grove] = TERRAIN.canopy_max[TerrainType.FOREST]
        self._stamp_waterholes(blueprint, row, column, radius)

    def _stamp_vents(self, blueprint: WorldBlueprint, row: int, column: int, radius: int) -> None:
        field = disc(blueprint.shape, row, column, radius)
        blueprint.terrain[field] = TerrainType.VOLCANIC
        blueprint.canopy[field] = 0.0
        blueprint.vents[disc(blueprint.shape, row, column, max(1, radius // 3))] = True

    def _stamp_kopjes(self, blueprint: WorldBlueprint, row: int, column: int, radius: int) -> None:
        blueprint.terrain[disc(blueprint.shape, row, column, max(1, radius // 2))] = TerrainType.ROCK

    def _stamp_caves(self, blueprint: WorldBlueprint, row: int, column: int, radius: int) -> None:
        region = disc(blueprint.shape, row, column, radius)
        open_cells = (self._rng.random(blueprint.shape) > CAVE_FILL_PROBABILITY) & region
        for _ in range(CAVE_SMOOTHING_PASSES):
            neighbors = sum(
                np.roll(open_cells, (dy, dx), axis=(0, 1)).astype(int)
                for dy in (-1, 0, 1)
                for dx in (-1, 0, 1)
                if (dy, dx) != (0, 0)
            )
            open_cells = ((neighbors >= 5) | (open_cells & (neighbors >= 4))) & region
        blueprint.terrain[region & ~open_cells] = TerrainType.ROCK
        blueprint.terrain[open_cells] = TerrainType.CAVE
        blueprint.canopy[region] = 0.0

    def _stamp_wadi(self, blueprint: WorldBlueprint, row: int, column: int, radius: int) -> None:
        height, width = blueprint.shape
        length = width // 2
        columns = (column + np.arange(length)) % width
        rows = (row + np.round(radius * np.sin(np.arange(length) / 6.0)).astype(int)) % height
        blueprint.wadi[rows, columns] = True


class WorldBuilder:
    def __init__(self, preset: WorldPreset, rng: np.random.Generator) -> None:
        self._preset = preset
        self._rng = rng
        height, width = preset.grid.height, preset.grid.width
        self._noise = PeriodicNoise(height, width, rng)

    def build(self) -> WorldBlueprint:
        preset = self._preset
        shape = (preset.grid.height, preset.grid.width)
        elevation = ElevationBuilder(self._noise).build(preset)
        waters = WaterBuilder(preset)
        sea_level = waters.sea_level(elevation)
        sea = elevation < sea_level
        land_range = max(1e-6, 1.0 - max(sea_level, 0.0))
        elevation_m = (
            np.clip(elevation - max(sea_level, 0.0), 0.0, None) / land_range * preset.terrain.max_elevation_m
        ).astype(np.float32)
        substellar = self._substellar_cosine(shape)
        temperature = ThermalBaseline(preset.climate).annual_mean(elevation_m, substellar)
        moisture = self._moisture(elevation, sea)
        deep_threshold = max(sea_level - float(elevation.min()), 1e-6) * preset.terrain.deep_water_depth_fraction
        rock_threshold = float(np.quantile(elevation, preset.terrain.rock_elevation_fraction))
        terrain = BiomeClassifier().classify(
            elevation, sea_level, deep_threshold, rock_threshold, temperature, moisture
        )
        base_water = np.zeros(shape, dtype=np.float32)
        base_water[terrain == TerrainType.SHALLOW_WATER] = SHALLOW_WATER_DEPTH_M
        base_water[terrain == TerrainType.DEEP_WATER] = DEEP_WATER_DEPTH_M
        rivers = waters.river_mask(elevation, sea)
        terrain[rivers] = TerrainType.SHALLOW_WATER
        base_water[rivers] = RIVER_DEPTH_M
        blueprint = WorldBlueprint(
            terrain=terrain,
            elevation_normalized=elevation,
            elevation_m=elevation_m,
            base_water=base_water,
            moisture=moisture,
            canopy=np.zeros(shape, dtype=np.float32),
            flood_mask=self._flood_mask(elevation, sea_level, terrain),
            rift_mask=np.zeros(shape, dtype=bool),
            inner_band=self._inner_band(shape),
            substellar_cosine=substellar,
            vents=np.zeros(shape, dtype=bool),
            wadi=np.zeros(shape, dtype=bool),
        )
        blueprint.canopy = (TERRAIN.canopy_max[terrain] * (0.8 + 0.2 * self._noise.octave(8))).astype(np.float32)
        stamper = FeatureStamper(self._rng)
        for stamp in preset.terrain.feature_stamps:
            stamper.apply(stamp, blueprint)
        blueprint.rift_mask = self._rift_mask(shape)
        return blueprint

    def _moisture(self, elevation: FloatGrid, sea: np.ndarray) -> FloatGrid:
        terrain = self._preset.terrain
        reach = max(2, int(terrain.moisture_water_reach_patches))
        proximity = np.exp(-distance_to(sea, reach * 3) / reach) if sea.any() else np.zeros_like(elevation)
        variation = (self._noise.fractal(terrain.lattice_cells * 2, 3, 0.5) - 0.5) * 2.0 * MOISTURE_VARIATION
        highland = HIGHLAND_DRYING * np.clip(elevation - 0.6, 0.0, None) / 0.4
        base = terrain.moisture_base + (1.0 - terrain.moisture_base) * 0.5 * proximity
        return np.clip(base + variation - highland, 0.0, 1.0).astype(np.float32)

    def _flood_mask(self, elevation: FloatGrid, sea_level: float, terrain: np.ndarray) -> np.ndarray:
        pulse = self._preset.disturbances.flood_pulse
        if pulse is None:
            return np.zeros(terrain.shape, dtype=bool)
        land = ~np.isin(terrain, (TerrainType.DEEP_WATER, TerrainType.SHALLOW_WATER))
        return land & (elevation < max(sea_level, 0.0) + pulse.floodplain_elevation_fraction)

    def _inner_band(self, shape: tuple[int, int]) -> np.ndarray:
        height, width = shape
        rows = np.arange(height)
        inner_rows = (rows >= height // 4) & (rows < 3 * height // 4)
        return np.repeat(inner_rows[:, None], width, axis=1)

    def _rift_mask(self, shape: tuple[int, int]) -> np.ndarray:
        rift = self._preset.disturbances.rift
        mask = np.zeros(shape, dtype=bool)
        if rift is None:
            return mask
        height, width = shape
        columns = np.arange(width)
        for center in (height // 4, 3 * height // 4):
            wave = center + np.round(RIFT_WAVINESS_PATCHES * np.sin(2.0 * math.pi * columns / width * 3)).astype(int)
            for offset in range(-(rift.channel_width // 2), rift.channel_width // 2 + 1):
                mask[(wave + offset) % height, columns] = True
        return mask

    def _substellar_cosine(self, shape: tuple[int, int]) -> FloatGrid:
        height, width = shape
        rows = (np.arange(height) - height / 2.0)[:, None]
        columns = (np.arange(width) - width / 2.0)[None, :]
        distance = np.sqrt(rows**2 + columns**2)
        farthest = math.hypot(height / 2.0, width / 2.0)
        return np.cos(math.pi * distance / farthest).astype(np.float32)
