from __future__ import annotations

import numpy as np

from lifeform.config.parameters import EcologyParameters
from lifeform.config.world_preset import WorldPreset
from lifeform.core.geometry import Position, TorusMetric
from lifeform.core.randomness import RandomStreams
from lifeform.core.time import Calendar
from lifeform.world.acoustics import SoundBoard
from lifeform.world.climate import Climate, ClimateState, Geography
from lifeform.world.entities import CarcassRegistry, DenRegistry, FoodCaches, TerritoryMarks
from lifeform.world.fields import EnvironmentalFields
from lifeform.world.generation.blueprint import WorldBlueprint
from lifeform.world.terrain import DEEP_WATER_DEPTH_M, IMPASSABLE, SHALLOW_WATER_DEPTH_M, TERRAIN, TerrainType

FLOOD_SHALLOW_DEPTH_M = 0.3
FLOOD_DEEP_DEPTH_M = 1.0
SWIM_SKILL_FOR_DEEP_WATER = 0.5
DEEP_SWIM_BASE_COST = 2.5
DEEP_SWIM_SKILL_DISCOUNT = 1.5
SNOW_COST_PER_CM = 0.02


class World:
    def __init__(
        self,
        preset: WorldPreset,
        ecology: EcologyParameters,
        blueprint: WorldBlueprint,
        productivity_scale: float,
        streams: RandomStreams,
    ) -> None:
        self.preset = preset
        self.ecology = ecology
        self.productivity_scale = productivity_scale
        self.calendar = Calendar(
            ticks_per_day=preset.calendar.ticks_per_day,
            days_per_season=preset.calendar.days_per_season,
            season_names=preset.calendar.season_names,
            days_per_lunar_cycle=preset.calendar.days_per_lunar_cycle,
        )
        self.metric = TorusMetric(preset.grid.width, preset.grid.height)
        self.terrain = blueprint.terrain
        self.elevation_m = blueprint.elevation_m
        self.flood_mask = blueprint.flood_mask
        self.rift_mask = blueprint.rift_mask
        self.inner_band = blueprint.inner_band
        self.wadi = blueprint.wadi
        self.substellar_cosine = blueprint.substellar_cosine
        self.fields = EnvironmentalFields(
            blueprint.terrain, blueprint.canopy, blueprint.base_water, blueprint.moisture, productivity_scale, ecology
        )
        self.fields.toxin.vents = blueprint.vents.copy()
        self.climate = Climate(preset.climate, self.calendar, self._geography(), streams.stream("climate"))
        self.climate_state: ClimateState = self.climate.advance(0, self.fields.canopy)
        self.carcasses = CarcassRegistry(self.metric)
        self.dens = DenRegistry()
        self.marks = TerritoryMarks(self.metric, ecology.social.territory_mark_half_life_ticks)
        self.caches = FoodCaches()
        self.sounds = SoundBoard()
        self.tick = 0

    @property
    def width(self) -> int:
        return self.metric.width

    @property
    def height(self) -> int:
        return self.metric.height

    def terrain_at(self, position: Position) -> TerrainType:
        base = TerrainType(int(self.terrain[position.y, position.x]))
        if base in (TerrainType.DEEP_WATER, TerrainType.SHALLOW_WATER):
            return base
        depth = self.water_depth(position)
        if depth >= FLOOD_DEEP_DEPTH_M:
            return TerrainType.DEEP_WATER
        if depth >= FLOOD_SHALLOW_DEPTH_M:
            return TerrainType.SHALLOW_WATER
        return base

    def water_depth(self, position: Position) -> float:
        return float(self.fields.hydrology.surface_water[position.y, position.x])

    def is_passable(self, position: Position, swim_skill: float) -> bool:
        return self.move_cost(position, swim_skill) != IMPASSABLE

    def move_cost(self, position: Position, swim_skill: float) -> float:
        terrain = self.terrain_at(position)
        if terrain == TerrainType.DEEP_WATER:
            if swim_skill < SWIM_SKILL_FOR_DEEP_WATER:
                return IMPASSABLE
            return DEEP_SWIM_BASE_COST - DEEP_SWIM_SKILL_DISCOUNT * swim_skill
        snow = float(self.fields.hydrology.snow_depth[position.y, position.x])
        return float(TERRAIN.move_cost[terrain]) + SNOW_COST_PER_CM * snow

    def cover(self, position: Position) -> float:
        return float(TERRAIN.cover[self.terrain_at(position)])

    def sight_opacity(self, position: Position) -> float:
        return float(TERRAIN.sight_opacity[self.terrain_at(position)])

    def temperature(self, position: Position) -> float:
        return float(self.climate_state.temperature[position.y, position.x])

    def light(self, position: Position) -> float:
        return float(self.climate_state.light[position.y, position.x])

    def canopy(self, position: Position) -> float:
        return float(self.fields.canopy[position.y, position.x])

    def is_burning(self, position: Position) -> bool:
        return bool(self.fields.fire.burning[position.y, position.x])

    def drinkable(self, position: Position) -> bool:
        return self.fields.hydrology.drinkable(position.x, position.y, self.temperature(position))

    def drinkable_near(self, position: Position) -> Position | None:
        for candidate in (position, *self.metric.neighbors(position)):
            if self.drinkable(candidate):
                return candidate
        return None

    def set_terrain(self, mask: np.ndarray, terrain: TerrainType) -> None:
        self.terrain[mask] = terrain
        if terrain in (TerrainType.DEEP_WATER, TerrainType.SHALLOW_WATER):
            depth = DEEP_WATER_DEPTH_M if terrain == TerrainType.DEEP_WATER else SHALLOW_WATER_DEPTH_M
            self.fields.hydrology.base_water[mask] = depth
            self.fields.hydrology.surface_water[mask] = np.maximum(self.fields.hydrology.surface_water[mask], depth)
        self.fields.canopy[mask] = np.minimum(self.fields.canopy[mask], TERRAIN.canopy_max[terrain])
        self.refresh_after_terrain_change()

    def refresh_after_terrain_change(self) -> None:
        self.fields.vegetation.refresh_capacity(self.terrain, self.fields.canopy)
        self.fields.scent.refresh_terrain(self.terrain)
        self.climate.refresh_geography(self._geography())

    def annual_mean_temperature(self, position: Position) -> float:
        return float(self.climate.annual_mean_temperature()[position.y, position.x])

    def _geography(self) -> Geography:
        return Geography(self.elevation_m, self.terrain, self.inner_band, self.substellar_cosine)
