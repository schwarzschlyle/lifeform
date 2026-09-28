from __future__ import annotations

import math

import numpy as np

from lifeform.config.world_preset import DisturbanceConfig
from lifeform.core.events import EventKind
from lifeform.simulation.context import TickContext
from lifeform.world.field_math import FloatGrid
from lifeform.world.generation.builder import disc
from lifeform.world.terrain import FoodLayer, TerrainType

FUEL_LAYERS = (FoodLayer.GRASS, FoodLayer.BROWSE)
BURNABLE = (
    TerrainType.GRASSLAND,
    TerrainType.SAVANNA,
    TerrainType.FOREST,
    TerrainType.RAINFOREST,
    TerrainType.TUNDRA,
    TerrainType.WETLAND,
)
LAVA_DAMAGE = 1.0
ASH_VEGETATION_SURVIVAL = 0.2
ASH_TOXIN = 0.3
WADI_DEPTH_M = 0.3
WADI_FLOW_TICKS = 12
RAFTING_MIN_DISTANCE_FRACTION = 0.25
SHALLOW_PHASE = 0.5
MINOR_LAVA_RADIUS = 4
MINOR_ASH_RADIUS = 15
RAFT_LANDING_ATTEMPTS = 20


class DisturbanceDirector:
    def __init__(self, config: DisturbanceConfig, rng: np.random.Generator) -> None:
        self._config = config
        self._rng = rng
        self._wadi_ticks_left = 0
        self._rift_started = False

    @property
    def fire_damage_per_tick(self) -> float:
        return self._config.fire_damage_per_tick

    def apply(self, context: TickContext) -> None:
        self._wildfire(context)
        self._flood_pulse(context)
        self._droughts(context)
        self._eruptions(context)
        self._rift(context)
        self._epidemic(context)
        self._rafting(context)
        self._wadi(context)

    def _fuel_and_dryness(self, context: TickContext) -> tuple[FloatGrid, FloatGrid]:
        vegetation = context.world.fields.vegetation
        fuel = sum(vegetation.biomass[layer] for layer in FUEL_LAYERS)
        capacity = sum(vegetation.capacity[layer] for layer in FUEL_LAYERS)
        fuel_fraction = np.clip(fuel / np.maximum(capacity, 1e-6), 0.0, 1.0)
        burnable = np.isin(context.world.terrain, BURNABLE)
        dryness = 1.0 - context.world.fields.hydrology.soil_moisture
        return (fuel_fraction * burnable).astype(np.float32), dryness.astype(np.float32)

    def _wildfire(self, context: TickContext) -> None:
        config = self._config
        world = context.world
        fire = world.fields.fire
        if config.lightning_fire_probability <= 0.0 and not fire.burning.any():
            return
        fuel, dryness = self._fuel_and_dryness(context)
        if world.climate_state.storm and self._rng.random() < config.lightning_fire_probability:
            self._ignite_by_lightning(context, fuel * dryness)
        if fire.burning.any():
            burning = fire.burning.astype(np.float32)
            neighbors = sum(
                np.roll(burning, (dy, dx), axis=(0, 1)) for dy in (-1, 0, 1) for dx in (-1, 0, 1) if (dy, dx) != (0, 0)
            )
            chance = 1.0 - (1.0 - config.fire_spread_probability * fuel * dryness) ** neighbors
            fire.ignite(self._rng.random(chance.shape) < chance, config.fire_burn_ticks)
            world.fields.vegetation.burn(fire.burning)
            world.fields.canopy[fire.burning] *= context.services.ecology.vegetation.fire_canopy_survival
        fire.advance()

    def _ignite_by_lightning(self, context: TickContext, flammability: FloatGrid) -> None:
        total = float(flammability.sum())
        if total <= 0.0:
            return
        flat = int(self._rng.choice(flammability.size, p=(flammability / total).ravel()))
        row, column = divmod(flat, flammability.shape[1])
        mask = np.zeros(flammability.shape, dtype=bool)
        mask[row, column] = True
        if context.world.fields.fire.ignite(mask, self._config.fire_burn_ticks):
            context.emit(EventKind.FIRE_START, position=context.world.metric.wrap(column, row))

    def _flood_pulse(self, context: TickContext) -> None:
        pulse = self._config.flood_pulse
        if pulse is None:
            return
        phase = context.world.calendar.year_fraction(context.tick) - pulse.peak_year_fraction
        context.world.fields.hydrology.flood_offset_m = pulse.amplitude_m * max(0.0, math.cos(2.0 * math.pi * phase))

    def _droughts(self, context: TickContext) -> None:
        factor = 1.0
        for drought in self._config.droughts:
            if drought.tick <= context.tick < drought.tick + drought.duration_ticks:
                factor = min(factor, drought.precipitation_factor)
                if context.tick == drought.tick:
                    context.emit(EventKind.DROUGHT_START, duration=drought.duration_ticks)
        context.world.climate.drought_factor = factor

    def _eruptions(self, context: TickContext) -> None:
        for eruption in self._config.eruptions:
            if eruption.tick == context.tick:
                self._erupt(context, eruption.lava_radius, eruption.ash_radius)
        if self._config.eruption_rate_per_tick > 0.0 and self._rng.random() < self._config.eruption_rate_per_tick:
            self._erupt(context, MINOR_LAVA_RADIUS, MINOR_ASH_RADIUS)

    def _erupt(self, context: TickContext, lava_radius: int, ash_radius: int) -> None:
        world = context.world
        vents = np.argwhere(world.fields.toxin.vents)
        if len(vents):
            row, column = (int(value) for value in vents[int(self._rng.integers(len(vents)))])
        else:
            row, column = int(self._rng.integers(world.height)), int(self._rng.integers(world.width))
        shape = (world.height, world.width)
        lava = disc(shape, row, column, lava_radius)
        ash = disc(shape, row, column, ash_radius)
        world.fields.vegetation.biomass[:, ash] *= ASH_VEGETATION_SURVIVAL
        world.fields.toxin.level[ash] = np.clip(world.fields.toxin.level[ash] + ASH_TOXIN, 0.0, 1.0)
        world.fields.toxin.vents[disc(shape, row, column, 1)] = True
        world.set_terrain(lava, TerrainType.VOLCANIC)
        for organism in context.population.living():
            if lava[organism.position.y, organism.position.x]:
                organism.body.take_damage("disaster", LAVA_DAMAGE, context.tick)
        context.emit(
            EventKind.ERUPTION, position=world.metric.wrap(column, row), lava_radius=lava_radius, ash_radius=ash_radius
        )

    def _rift(self, context: TickContext) -> None:
        rift = self._config.rift
        if rift is None or context.tick < rift.open_tick or context.tick > rift.open_tick + rift.duration_ticks:
            return
        world = context.world
        if not self._rift_started:
            self._rift_started = True
            context.emit(EventKind.RIFT_OPEN, duration=rift.duration_ticks)
        progress = (context.tick - rift.open_tick) / max(1, rift.duration_ticks)
        target = TerrainType.SHALLOW_WATER if progress < SHALLOW_PHASE else TerrainType.DEEP_WATER
        if context.tick in (rift.open_tick, rift.open_tick + round(SHALLOW_PHASE * rift.duration_ticks)):
            world.set_terrain(world.rift_mask, target)

    def _epidemic(self, context: TickContext) -> None:
        epidemic = self._config.epidemic
        if epidemic is None or context.tick != epidemic.tick:
            return
        counts = context.population.species_counts()
        if not counts:
            return
        species_id = max(counts, key=counts.__getitem__)
        candidates = [organism for organism in context.population.living() if organism.species_id == species_id]
        patient = candidates[int(self._rng.integers(len(candidates)))]
        strain = context.services.strains.register(
            epidemic.transmission,
            epidemic.virulence,
            epidemic.latent_ticks,
            epidemic.infectious_ticks,
            epidemic.immunity_ticks,
            epidemic.environmental_shedding,
            epidemic.environmental_half_life_ticks,
            patient.genome.genotype,
            epidemic.host_distance,
        )
        if context.services.transmission.infect(patient, strain):
            context.emit(EventKind.OUTBREAK, (patient.id,), patient.position, strain=strain.strain_id)

    def _rafting(self, context: TickContext) -> None:
        if self._config.rafting_probability <= 0.0 or self._rng.random() >= self._config.rafting_probability:
            return
        world = context.world
        coastal = [
            organism
            for organism in context.population.living()
            if any(
                world.terrain_at(neighbor) == TerrainType.DEEP_WATER
                for neighbor in world.metric.neighbors(organism.position)
            )
        ]
        if not coastal:
            return
        rafter = coastal[int(self._rng.integers(len(coastal)))]
        shores = np.argwhere(self._shore_mask(context))
        if len(shores) == 0:
            return
        minimum = RAFTING_MIN_DISTANCE_FRACTION * world.width
        for _ in range(RAFT_LANDING_ATTEMPTS):
            row, column = (int(value) for value in shores[int(self._rng.integers(len(shores)))])
            landing = world.metric.wrap(column, row)
            if world.metric.distance(rafter.position, landing) >= minimum:
                origin = rafter.position
                rafter.body.position = landing
                context.emit(EventKind.RAFTING, (rafter.id,), landing, origin=(origin.x, origin.y))
                return

    @staticmethod
    def _shore_mask(context: TickContext) -> np.ndarray:
        terrain = context.world.terrain
        deep = terrain == TerrainType.DEEP_WATER
        land = ~np.isin(terrain, (TerrainType.DEEP_WATER, TerrainType.SHALLOW_WATER))
        near_deep = np.zeros_like(deep)
        for dy in (-1, 0, 1):
            for dx in (-1, 0, 1):
                near_deep |= np.roll(deep, (dy, dx), axis=(0, 1))
        return land & near_deep

    def _wadi(self, context: TickContext) -> None:
        world = context.world
        if not world.wadi.any():
            return
        if world.climate_state.storm:
            self._wadi_ticks_left = WADI_FLOW_TICKS
        hydrology = world.fields.hydrology
        if self._wadi_ticks_left > 0:
            self._wadi_ticks_left -= 1
            hydrology.base_water[world.wadi] = WADI_DEPTH_M
        else:
            hydrology.base_water[world.wadi] = 0.0
