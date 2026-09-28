from __future__ import annotations

import math

import numpy as np

from lifeform.simulation.context import TickContext
from lifeform.simulation.disturbances import DisturbanceDirector
from lifeform.world.fields import DRINKABLE_DEPTH_M, GrowthConditions
from lifeform.world.terrain import TERRAIN, FoodLayer, TerrainType


class EnvironmentPhase:
    name = "environment"

    def __init__(self, disturbances: DisturbanceDirector) -> None:
        self._disturbances = disturbances

    def run(self, context: TickContext) -> None:
        world = context.world
        world.tick = context.tick
        world.sounds.rotate()
        world.climate_state = world.climate.advance(context.tick, world.fields.canopy)
        self._disturbances.apply(context)
        state = world.climate_state
        flood = world.flood_mask if world.preset.disturbances.flood_pulse is not None else None
        world.fields.hydrology.update(state.precipitation, state.temperature, flood)
        growth = world.fields.vegetation.grow(self._conditions(context))
        world.fields.nutrients.update(growth)
        self._regrow_canopy(context)
        context.services.decay.update(world)
        self._emit_landscape_scents(context)
        world.fields.scent.update(state.wind, state.raining)
        world.fields.toxin.update()
        water = np.isin(world.terrain, (TerrainType.SHALLOW_WATER, TerrainType.WETLAND))
        world.fields.pathogen.update(water)
        world.marks.decay()

    def _conditions(self, context: TickContext) -> GrowthConditions:
        world = context.world
        vegetation = context.services.ecology.vegetation
        year = world.calendar.year_fraction(context.tick)
        offset = (year - vegetation.fruiting_peak_year_fraction + 0.5) % 1.0 - 0.5
        pulse = vegetation.fruiting_off_season_fraction + math.exp(
            -((offset / vegetation.fruiting_width_year_fraction) ** 2)
        )
        recently_burnt = world.fields.fire.burn_age < world.calendar.ticks_per_season
        flush = np.where(recently_burnt, vegetation.fire_grass_flush_multiplier, 1.0).astype(np.float32)
        state = world.climate_state
        return GrowthConditions(
            state.temperature,
            world.fields.hydrology.soil_moisture,
            state.mean_light,
            world.fields.nutrients.level,
            pulse,
            flush,
        )

    def _regrow_canopy(self, context: TickContext) -> None:
        world = context.world
        vegetation = context.services.ecology.vegetation
        ceiling = TERRAIN.canopy_max[world.terrain]
        canopy = world.fields.canopy
        growth = vegetation.canopy_regrowth_per_tick * canopy * (1.0 - canopy / np.maximum(ceiling, 1e-6))
        world.fields.canopy = np.clip(canopy + growth, 0.0, ceiling).astype(np.float32)
        if context.tick % vegetation.capacity_refresh_interval_ticks == 0:
            world.fields.vegetation.refresh_capacity(world.terrain, world.fields.canopy)

    def _emit_landscape_scents(self, context: TickContext) -> None:
        world = context.world
        scent = context.services.ecology.scent
        fields = world.fields
        fields.scent.emit_field("fruit_aroma", fields.vegetation.biomass[FoodLayer.FRUIT] * scent.fruit_emission_per_kg)
        drinkable = (fields.hydrology.surface_water >= DRINKABLE_DEPTH_M).astype(np.float32)
        fields.scent.emit_field("water", drinkable * scent.water_emission)
        fields.scent.emit_field("smoke", fields.fire.intensity * scent.smoke_emission_per_intensity)
