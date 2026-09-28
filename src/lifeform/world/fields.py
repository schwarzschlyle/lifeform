from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from lifeform.config.parameters import (
    DiseaseParameters,
    EcologyParameters,
    FoodLayerParameters,
    HydrologyParameters,
    NutrientParameters,
    ScentParameters,
    ToxinParameters,
    VegetationParameters,
)
from lifeform.world.field_math import (
    FloatGrid,
    advect,
    decay_factor,
    diffuse,
    gaussian_response,
    laplacian,
    monod,
)
from lifeform.world.terrain import TERRAIN, FoodLayer, TerrainType

DRINKABLE_DEPTH_M = 0.05
FROZEN_WATER_TEMPERATURE_C = -2.0
GROUND_LAYERS = (FoodLayer.GRASS, FoodLayer.SEEDS, FoodLayer.INVERTEBRATES)
FLAMMABLE_LAYERS = (FoodLayer.GRASS, FoodLayer.BROWSE, FoodLayer.FRUIT, FoodLayer.SEEDS)


@dataclass(slots=True)
class GrowthConditions:
    temperature: FloatGrid
    soil_moisture: FloatGrid
    mean_light: FloatGrid
    nutrients: FloatGrid
    fruiting_pulse: float
    grass_flush: FloatGrid


class VegetationField:
    def __init__(
        self,
        terrain: np.ndarray,
        canopy: FloatGrid,
        productivity_scale: float,
        layers: dict[str, FoodLayerParameters],
        parameters: VegetationParameters,
    ) -> None:
        self._productivity_scale = productivity_scale
        self._layers = [layers[layer.key] for layer in FoodLayer]
        self._parameters = parameters
        self.capacity = self._capacity_for(terrain, canopy)
        self.biomass = (self.capacity * parameters.initial_fraction_of_capacity).astype(np.float32)

    def refresh_capacity(self, terrain: np.ndarray, canopy: FloatGrid) -> None:
        self.capacity = self._capacity_for(terrain, canopy)
        np.minimum(self.biomass, self._ceiling(), out=self.biomass)

    def grow(self, conditions: GrowthConditions) -> FloatGrid:
        total_growth = np.zeros(self.biomass.shape[1:], dtype=np.float32)
        for layer, parameters in zip(FoodLayer, self._layers, strict=True):
            grown = self._grown_layer(layer, parameters, conditions)
            total_growth += np.clip(grown - self.biomass[layer], 0.0, None)
            self.biomass[layer] = grown
        return total_growth

    def accessible(self, layer: FoodLayer, x: int, y: int, snow_depth_cm: float) -> float:
        amount = float(self.biomass[layer, y, x])
        if layer in GROUND_LAYERS:
            amount *= float(np.exp(-snow_depth_cm / self._parameters.snow_access_scale_cm))
        return amount

    def consume(self, layer: FoodLayer, x: int, y: int, amount_kg: float) -> float:
        taken = min(amount_kg, float(self.biomass[layer, y, x]))
        self.biomass[layer, y, x] -= taken
        return taken

    def burn(self, burning: np.ndarray) -> None:
        for layer in FLAMMABLE_LAYERS:
            self.biomass[layer][burning] *= self._parameters.burn_survival_fraction

    def trample(self, x: int, y: int) -> None:
        self.biomass[FoodLayer.GRASS, y, x] *= 1.0 - self._parameters.trample_fraction_per_pass

    def total(self, layer: FoodLayer) -> float:
        return float(self.biomass[layer].sum())

    def _ceiling(self) -> np.ndarray:
        return np.asarray(self.capacity * self._parameters.overshoot_fraction_of_capacity, dtype=np.float32)

    def _capacity_for(self, terrain: np.ndarray, canopy: FloatGrid) -> np.ndarray:
        capacity = TERRAIN.capacity[terrain].transpose(2, 0, 1) * self._productivity_scale
        canopy_max = np.maximum(TERRAIN.canopy_max[terrain], 1e-3)
        canopy_share = np.clip(canopy / canopy_max, self._parameters.min_canopy_share, 1.0)
        capacity[FoodLayer.BROWSE] *= canopy_share
        capacity[FoodLayer.FRUIT] *= canopy_share
        return capacity.astype(np.float32)

    def _grown_layer(
        self, layer: FoodLayer, parameters: FoodLayerParameters, conditions: GrowthConditions
    ) -> FloatGrid:
        biomass = self.biomass[layer]
        capacity = self.capacity[layer]
        environment = gaussian_response(
            conditions.temperature, parameters.thermal_optimum_c, parameters.thermal_breadth_c
        )
        environment = environment * monod(conditions.soil_moisture, self._parameters.moisture_half_saturation)
        environment = environment * monod(conditions.nutrients, self._parameters.nutrient_half_saturation)
        if parameters.needs_light:
            environment = environment * monod(conditions.mean_light, self._parameters.light_half_saturation)
        if layer == FoodLayer.FRUIT:
            environment = environment * conditions.fruiting_pulse
        if layer == FoodLayer.GRASS:
            environment = environment * conditions.grass_flush
        safe_capacity = np.maximum(capacity, 1e-6)
        growth = parameters.growth_rate_per_tick * environment * biomass * (1.0 - biomass / safe_capacity)
        spread = parameters.dispersal_rate * laplacian(biomass)
        floor = parameters.seed_floor_kg * (capacity > 0)
        ceiling = capacity * self._parameters.overshoot_fraction_of_capacity
        return np.clip(biomass + growth + spread + floor, 0.0, ceiling).astype(np.float32)


class Hydrology:
    def __init__(self, base_water: FloatGrid, moisture_base: FloatGrid, parameters: HydrologyParameters) -> None:
        self.base_water = base_water.astype(np.float32)
        self.surface_water = base_water.astype(np.float32).copy()
        self.soil_moisture = moisture_base.astype(np.float32).copy()
        self.snow_depth = np.zeros_like(base_water, dtype=np.float32)
        self.flood_offset_m = 0.0
        self._parameters = parameters

    def update(self, precipitation_mm: FloatGrid, temperature: FloatGrid, flood_mask: np.ndarray | None) -> None:
        snowing = temperature < 0.0
        warmth = np.clip(temperature, 0.0, None) / 10.0
        self._update_snow(precipitation_mm, temperature, snowing)
        self._update_soil(precipitation_mm, snowing, warmth)
        self._update_surface(precipitation_mm, snowing, warmth, flood_mask)

    def drinkable(self, x: int, y: int, temperature_c: float) -> bool:
        return bool(self.surface_water[y, x] >= DRINKABLE_DEPTH_M and temperature_c > FROZEN_WATER_TEMPERATURE_C)

    def drink(self, x: int, y: int, litres: float) -> None:
        depth = litres / self._parameters.litres_per_metre_of_patch_depth
        self.surface_water[y, x] = max(float(self.base_water[y, x]), float(self.surface_water[y, x]) - depth)

    def _update_snow(self, precipitation_mm: FloatGrid, temperature: FloatGrid, snowing: np.ndarray) -> None:
        parameters = self._parameters
        fallen = np.where(snowing, precipitation_mm * parameters.snow_cm_per_mm, 0.0)
        melted = np.clip(temperature, 0.0, None) * parameters.melt_cm_per_degree_tick
        self.snow_depth = np.clip(self.snow_depth + fallen - melted, 0.0, parameters.max_snow_cm).astype(np.float32)

    def _update_soil(self, precipitation_mm: FloatGrid, snowing: np.ndarray, warmth: FloatGrid) -> None:
        parameters = self._parameters
        infiltration = np.where(snowing, 0.0, precipitation_mm * parameters.infiltration_per_mm)
        drying = parameters.soil_drying_per_tick * (1.0 + parameters.heat_drying_per_10c * warmth) * self.soil_moisture
        recharge = parameters.lake_recharge_per_tick * (self.base_water > 0)
        self.soil_moisture = np.clip(self.soil_moisture + infiltration - drying + recharge, 0.0, 1.0).astype(np.float32)

    def _update_surface(
        self, precipitation_mm: FloatGrid, snowing: np.ndarray, warmth: FloatGrid, flood_mask: np.ndarray | None
    ) -> None:
        parameters = self._parameters
        ponded = np.where(snowing, 0.0, precipitation_mm / 1000.0 * parameters.ponding_fraction)
        evaporation = parameters.evaporation_m_per_tick_per_10c * warmth
        surface = np.clip(self.surface_water + ponded - evaporation, 0.0, None)
        surface = np.maximum(surface, self.base_water + self._flood_contribution(flood_mask))
        self.surface_water = np.minimum(surface, self.base_water + parameters.max_flood_above_base_m).astype(np.float32)

    def _flood_contribution(self, flood_mask: np.ndarray | None) -> FloatGrid:
        if flood_mask is None or self.flood_offset_m <= 0.0:
            return np.zeros_like(self.base_water)
        return np.where(flood_mask, self.flood_offset_m, 0.0).astype(np.float32)


class NutrientField:
    def __init__(self, shape: tuple[int, int], parameters: NutrientParameters) -> None:
        self.level = np.full(shape, parameters.initial_level, dtype=np.float32)
        self._parameters = parameters

    def deposit(self, x: int, y: int, amount: float) -> None:
        self.level[y, x] = min(1.0, float(self.level[y, x]) + amount)

    def update(self, growth_kg: FloatGrid) -> None:
        parameters = self._parameters
        uptake = parameters.uptake_per_kg_growth * growth_kg
        change = parameters.weathering_per_tick - parameters.leaching_rate_per_tick * self.level - uptake
        self.level = np.clip(self.level + change, 0.0, 1.0).astype(np.float32)


class ToxinField:
    def __init__(self, shape: tuple[int, int], parameters: ToxinParameters) -> None:
        self.level = np.zeros(shape, dtype=np.float32)
        self.vents = np.zeros(shape, dtype=bool)
        self._parameters = parameters

    def update(self) -> None:
        parameters = self._parameters
        emitted = self.vents * parameters.vent_emission_per_tick
        spread = diffuse(self.level, parameters.diffusion) * parameters.retention_per_tick
        self.level = np.clip(spread + emitted, 0.0, 1.0).astype(np.float32)


class FireField:
    def __init__(self, shape: tuple[int, int]) -> None:
        self.intensity = np.zeros(shape, dtype=np.float32)
        self.burn_ticks_left = np.zeros(shape, dtype=np.int16)
        self.burn_age = np.full(shape, 1_000_000, dtype=np.int32)

    @property
    def burning(self) -> np.ndarray:
        return self.burn_ticks_left > 0

    def ignite(self, mask: np.ndarray, burn_ticks: int) -> int:
        fresh = mask & ~self.burning
        self.burn_ticks_left[fresh] = burn_ticks
        self.intensity[fresh] = 1.0
        self.burn_age[fresh] = 0
        return int(fresh.sum())

    def advance(self) -> None:
        self.burn_ticks_left = np.clip(self.burn_ticks_left - 1, 0, None).astype(np.int16)
        self.intensity = np.where(self.burn_ticks_left > 0, self.intensity, 0.0).astype(np.float32)
        self.burn_age += 1


class ScentLandscape:
    FIXED_CHANNELS: tuple[str, ...] = ("fruit_aroma", "carrion", "blood", "water", "smoke", "alarm_pheromone")
    MUSK_PREFIX = "musk:"
    ESTRUS_PREFIX = "estrus:"

    def __init__(self, terrain: np.ndarray, parameters: ScentParameters) -> None:
        self._shape = (int(terrain.shape[0]), int(terrain.shape[1]))
        self._parameters = parameters
        self.channels: dict[str, FloatGrid] = {name: self._blank() for name in self.FIXED_CHANNELS}
        self.sources: dict[str, FloatGrid] = {name: self._blank() for name in self.FIXED_CHANNELS}
        self._terrain_decay = self._blank()
        self.refresh_terrain(terrain)

    def refresh_terrain(self, terrain: np.ndarray) -> None:
        multiplier = np.ones(self._shape, dtype=np.float32)
        multiplier[terrain == TerrainType.DEEP_WATER] = self._parameters.deep_water_decay_multiplier
        multiplier[terrain == TerrainType.SHALLOW_WATER] = self._parameters.shallow_water_decay_multiplier
        self._terrain_decay = multiplier

    def musk_channel(self, species_id: int) -> str:
        return self._species_channel(self.MUSK_PREFIX, species_id)

    def estrus_channel(self, species_id: int) -> str:
        return self._species_channel(self.ESTRUS_PREFIX, species_id)

    @classmethod
    def musk_name(cls, species_id: int) -> str:
        return f"{cls.MUSK_PREFIX}{species_id}"

    @classmethod
    def species_of(cls, channel: str) -> int | None:
        for prefix in (cls.MUSK_PREFIX, cls.ESTRUS_PREFIX):
            if channel.startswith(prefix):
                return int(channel.removeprefix(prefix))
        return None

    def _species_channel(self, prefix: str, species_id: int) -> str:
        name = f"{prefix}{species_id}"
        if name not in self.channels:
            self.channels[name] = self._blank()
            self.sources[name] = self._blank()
        return name

    def emit(self, channel: str, x: int, y: int, amount: float) -> None:
        self.sources[channel][y, x] += amount

    def emit_field(self, channel: str, amounts: FloatGrid) -> None:
        self.sources[channel] += amounts.astype(np.float32)

    def update(self, wind: tuple[float, float], raining: bool) -> None:
        rain_multiplier = self._parameters.rain_decay_multiplier if raining else 1.0
        for name, grid in self.channels.items():
            decay = np.clip(decay_factor(self._half_life(name)) * self._terrain_decay * rain_multiplier, 0.0, 1.0)
            moved = advect(diffuse(grid, self._parameters.diffusion), wind[0], wind[1])
            self.channels[name] = ((1.0 - decay) * moved + self.sources[name]).astype(np.float32)
            self.sources[name].fill(0.0)

    def forget_musk_of(self, living_species: set[int]) -> None:
        for name in list(self.channels):
            species_id = self.species_of(name)
            if species_id is not None and species_id not in living_species:
                del self.channels[name]
                del self.sources[name]

    def _half_life(self, channel: str) -> float:
        if channel.startswith(self.MUSK_PREFIX):
            return self._parameters.half_lives_ticks["musk"]
        if channel.startswith(self.ESTRUS_PREFIX):
            return self._parameters.half_lives_ticks["estrus"]
        return self._parameters.half_lives_ticks[channel]

    def _blank(self) -> FloatGrid:
        return np.zeros(self._shape, dtype=np.float32)


class PathogenField:
    def __init__(self, shape: tuple[int, int], parameters: DiseaseParameters) -> None:
        self._shape = shape
        self._parameters = parameters
        self.load: dict[int, FloatGrid] = {}
        self.half_lives: dict[int, float] = {}

    def shed(self, strain_id: int, x: int, y: int, amount: float, half_life_ticks: float) -> None:
        if strain_id not in self.load:
            self.load[strain_id] = np.zeros(self._shape, dtype=np.float32)
            self.half_lives[strain_id] = half_life_ticks
        self.load[strain_id][y, x] = min(1.0, float(self.load[strain_id][y, x]) + amount)

    def update(self, water_mask: np.ndarray) -> None:
        for strain_id, grid in list(self.load.items()):
            decay = decay_factor(self.half_lives[strain_id])
            spread = np.where(water_mask, diffuse(grid, self._parameters.water_diffusion), grid)
            self.load[strain_id] = (spread * (1.0 - decay)).astype(np.float32)
            if float(self.load[strain_id].max()) < self._parameters.field_extinction_level:
                del self.load[strain_id]
                del self.half_lives[strain_id]

    def total(self) -> FloatGrid:
        combined = np.zeros(self._shape, dtype=np.float32)
        for grid in self.load.values():
            combined += grid
        return np.clip(combined, 0.0, 1.0).astype(np.float32)


class EnvironmentalFields:
    def __init__(
        self,
        terrain: np.ndarray,
        canopy: FloatGrid,
        base_water: FloatGrid,
        moisture: FloatGrid,
        productivity_scale: float,
        ecology: EcologyParameters,
    ) -> None:
        shape = (int(terrain.shape[0]), int(terrain.shape[1]))
        self.canopy = canopy.astype(np.float32)
        self.vegetation = VegetationField(
            terrain, self.canopy, productivity_scale, ecology.food_layers, ecology.vegetation
        )
        self.hydrology = Hydrology(base_water, moisture, ecology.hydrology)
        self.nutrients = NutrientField(shape, ecology.nutrients)
        self.toxin = ToxinField(shape, ecology.toxin)
        self.fire = FireField(shape)
        self.scent = ScentLandscape(terrain, ecology.scent)
        self.pathogen = PathogenField(shape, ecology.disease)
