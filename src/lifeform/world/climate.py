from __future__ import annotations

import math
from dataclasses import dataclass
from enum import IntEnum

import numpy as np

from lifeform.config.world_preset import ClimateConfig, RegionalDrift, WeatherProfile
from lifeform.core.time import Calendar
from lifeform.world.field_math import FloatGrid, advect
from lifeform.world.generation.noise import PeriodicNoise
from lifeform.world.terrain import TERRAIN, TerrainType
from lifeform.world.thermal_baseline import ThermalBaseline

TWILIGHT_HOURS = 1.0
TWILIGHT_LIGHT = 0.08
MOONLIGHT_PEAK = 0.05
CLOUD_LIGHT_LOSS = 0.6
CANOPY_LIGHT_LOSS = 0.7
TIDAL_LIGHT_PEAK = 0.6
SUMMER_PHASE_OFFSET = 0.125
DIURNAL_PEAK_HOUR_OFFSET = 9.0
CLOUD_DIURNAL_DAMPING = 0.5
RAIN_CELL_CELLS = 6
RAIN_CELL_THRESHOLD = 0.45
WIND_JITTER_DEGREES = 12.0
STORM_WIND_MULTIPLIER = 2.0
WIND_RETURN_RATE = 0.1
RAIN_CELL_GAIN = 2.0
RAIN_BELT_GAIN = 2.0


class WeatherState(IntEnum):
    CLEAR = 0
    CLOUDY = 1
    FOG = 2
    RAIN = 3
    STORM = 4


WEATHER_CLOUD: dict[WeatherState, float] = {
    WeatherState.CLEAR: 0.0,
    WeatherState.CLOUDY: 0.6,
    WeatherState.FOG: 0.5,
    WeatherState.RAIN: 0.8,
    WeatherState.STORM: 1.0,
}

WEATHER_RAIN_MULTIPLIER: dict[WeatherState, float] = {
    WeatherState.CLEAR: 0.0,
    WeatherState.CLOUDY: 0.0,
    WeatherState.FOG: 0.0,
    WeatherState.RAIN: 1.0,
    WeatherState.STORM: 3.0,
}

RAIN_PROPENSITY: dict[WeatherProfile, tuple[float, float, float, float]] = {
    "temperate": (0.35, 0.25, 0.35, 0.30),
    "tropical_wet_dry": (0.60, 0.45, 0.08, 0.03),
    "arid": (0.04, 0.02, 0.05, 0.06),
    "boreal": (0.30, 0.35, 0.35, 0.30),
    "rainforest": (0.60, 0.55, 0.60, 0.65),
    "volcanic": (0.30, 0.25, 0.35, 0.35),
    "constant": (0.20, 0.20, 0.20, 0.20),
}

WEATHER_PERSISTENCE = 0.8
FOG_WEIGHT = 0.1
CLOUDY_WEIGHT = 0.5
STORM_SHARE_OF_RAIN = 0.3


class WeatherMarkovChain:
    def __init__(self, profile: WeatherProfile, rng: np.random.Generator) -> None:
        self._propensity = RAIN_PROPENSITY[profile]
        self._rng = rng
        self.state = WeatherState.CLEAR

    def advance(self, season_index: int) -> WeatherState:
        if self._rng.random() < WEATHER_PERSISTENCE:
            return self.state
        propensity = self._propensity[season_index % len(self._propensity)]
        weights = np.array([1.0 - propensity, CLOUDY_WEIGHT, FOG_WEIGHT, propensity, propensity * STORM_SHARE_OF_RAIN])
        self.state = WeatherState(int(self._rng.choice(len(weights), p=weights / weights.sum())))
        return self.state


@dataclass(slots=True)
class Geography:
    elevation_m: FloatGrid
    terrain: np.ndarray
    inner_band: np.ndarray
    substellar_cosine: FloatGrid


@dataclass(slots=True)
class ClimateState:
    weather: WeatherState
    cloud: float
    temperature: FloatGrid
    light: FloatGrid
    mean_light: FloatGrid
    precipitation: FloatGrid
    wind: tuple[float, float]
    daylight: bool

    @property
    def raining(self) -> bool:
        return self.weather in (WeatherState.RAIN, WeatherState.STORM)

    @property
    def storm(self) -> bool:
        return self.weather == WeatherState.STORM


class Climate:
    def __init__(
        self, config: ClimateConfig, calendar: Calendar, geography: Geography, rng: np.random.Generator
    ) -> None:
        self._config = config
        self._calendar = calendar
        self._geography = geography
        self._rng = rng
        self._chain = WeatherMarkovChain(config.weather_profile, rng)
        height, width = geography.terrain.shape
        self._rain_cells = PeriodicNoise(height, width, rng).fractal(RAIN_CELL_CELLS, 3, 0.5)
        self._rain_offset = (0.0, 0.0)
        self._anomaly = 0.0
        self._wind_degrees = config.prevailing_wind_degrees
        self._base = self._static_base_temperature()
        self._mean_light = np.full((height, width), 0.4, dtype=np.float32)
        self.drought_factor = 1.0

    def refresh_geography(self, geography: Geography) -> None:
        self._geography = geography
        self._base = self._static_base_temperature()

    def annual_mean_temperature(self) -> FloatGrid:
        return self._base

    def advance(self, tick: int, canopy: FloatGrid) -> ClimateState:
        weather = self._chain.advance(self._calendar.season_index(tick))
        cloud = WEATHER_CLOUD[weather]
        wind = self._advance_wind(weather)
        self._anomaly = self._config.anomaly_persistence * self._anomaly + float(
            self._rng.normal(0.0, self._config.anomaly_sigma_c)
        )
        temperature = self._temperature(tick, cloud)
        light = self._light(tick, cloud, canopy)
        self._mean_light += (light - self._mean_light) / self._calendar.ticks_per_day
        precipitation = self._precipitation(tick, weather, wind)
        daylight = self._sun_height(tick) > 0.0
        return ClimateState(weather, cloud, temperature, light, self._mean_light.copy(), precipitation, wind, daylight)

    def _static_base_temperature(self) -> FloatGrid:
        baseline = ThermalBaseline(self._config).annual_mean(
            self._geography.elevation_m, self._geography.substellar_cosine
        )
        return (baseline + TERRAIN.temperature_offset[self._geography.terrain]).astype(np.float32)

    def _temperature(self, tick: int, cloud: float) -> FloatGrid:
        config = self._config
        seasonal = 0.0
        diurnal = np.zeros_like(self._base)
        if not config.tidally_locked:
            year_phase = self._calendar.year_fraction(tick) - SUMMER_PHASE_OFFSET
            seasonal = config.seasonal_amplitude_c * math.sin(2.0 * math.pi * year_phase)
            hour = self._calendar.hour_of_day(tick)
            daily_wave = math.sin(2.0 * math.pi * (hour - DIURNAL_PEAK_HOUR_OFFSET) / self._calendar.hours_per_day)
            damping = 1.0 - TERRAIN.diurnal_damping[self._geography.terrain]
            diurnal = config.diurnal_amplitude_c * damping * (1.0 - CLOUD_DIURNAL_DAMPING * cloud) * daily_wave
        drift = self._drift(tick) + self._regional_temperature(tick)
        temperature = self._base + seasonal + diurnal + self._anomaly + drift
        cave = self._geography.terrain == TerrainType.CAVE
        return np.where(cave, self._base, temperature).astype(np.float32)

    def _drift(self, tick: int) -> float:
        drift = self._config.drift
        if drift is None:
            return 0.0
        return drift.total_c * _ramp(tick, drift.start_tick, drift.end_tick)

    def _regional_temperature(self, tick: int) -> FloatGrid:
        total = np.zeros_like(self._base)
        for regional in self._config.regional_drifts:
            total += (
                self._band_mask(regional) * regional.temperature_c * _ramp(tick, regional.start_tick, regional.end_tick)
            )
        return total

    def _regional_precipitation_factor(self, tick: int) -> FloatGrid:
        factor = np.ones_like(self._base)
        for regional in self._config.regional_drifts:
            progress = _ramp(tick, regional.start_tick, regional.end_tick)
            local = 1.0 + (regional.precipitation_factor - 1.0) * progress
            factor = np.where(self._band_mask(regional), factor * local, factor)
        return factor.astype(np.float32)

    def _band_mask(self, regional: RegionalDrift) -> np.ndarray:
        inner = self._geography.inner_band
        return inner if regional.band == "inner" else ~inner

    def _sun_height(self, tick: int) -> float:
        if self._config.tidally_locked:
            return 1.0
        year_phase = self._calendar.year_fraction(tick) - SUMMER_PHASE_OFFSET
        half_day = self._calendar.hours_per_day / 4.0 + self._config.day_length_amplitude_hours / 2.0 * math.sin(
            2.0 * math.pi * year_phase
        )
        noon = self._calendar.hours_per_day / 2.0
        rise, fall = noon - half_day, noon + half_day
        hour = self._calendar.hour_of_day(tick)
        if rise <= hour <= fall:
            return math.sin(math.pi * (hour - rise) / (fall - rise))
        if rise - TWILIGHT_HOURS <= hour < rise or fall < hour <= fall + TWILIGHT_HOURS:
            return 0.0
        return -1.0

    def _light(self, tick: int, cloud: float, canopy: FloatGrid) -> FloatGrid:
        if self._config.tidally_locked:
            sky = TIDAL_LIGHT_PEAK * np.clip(self._geography.substellar_cosine, 0.0, None)
        else:
            sun = self._sun_height(tick)
            moon = MOONLIGHT_PEAK * self._calendar.lunar_brightness(tick)
            level = max(sun, 0.0) + (TWILIGHT_LIGHT if sun == 0.0 else 0.0) + (moon if sun <= 0.0 else 0.0)
            sky = np.full(self._base.shape, level, dtype=np.float32)
        shaded = sky * (1.0 - CLOUD_LIGHT_LOSS * cloud) * (1.0 - CANOPY_LIGHT_LOSS * canopy)
        cave = self._geography.terrain == TerrainType.CAVE
        return np.where(cave, 0.0, shaded).astype(np.float32)

    def _advance_wind(self, weather: WeatherState) -> tuple[float, float]:
        self._wind_degrees += float(self._rng.normal(0.0, WIND_JITTER_DEGREES))
        pull = self._config.prevailing_wind_degrees - self._wind_degrees
        self._wind_degrees += WIND_RETURN_RATE * pull
        speed = self._config.wind_speed * (STORM_WIND_MULTIPLIER if weather == WeatherState.STORM else 1.0)
        radians = math.radians(self._wind_degrees)
        return speed * math.sin(radians), -speed * math.cos(radians)

    def _precipitation(self, tick: int, weather: WeatherState, wind: tuple[float, float]) -> FloatGrid:
        self._rain_cells = advect(self._rain_cells, wind[0], wind[1])
        intensity = self._config.rain_mm_per_tick * WEATHER_RAIN_MULTIPLIER[weather] * self.drought_factor
        if intensity <= 0.0:
            return np.zeros_like(self._base)
        cells = (
            np.clip((self._rain_cells - RAIN_CELL_THRESHOLD) / (1.0 - RAIN_CELL_THRESHOLD), 0.0, 1.0) * RAIN_CELL_GAIN
        )
        pattern = cells * self._rain_belt(tick) * self._regional_precipitation_factor(tick)
        return (intensity * pattern).astype(np.float32)

    def _rain_belt(self, tick: int) -> FloatGrid:
        belt = self._config.rain_belt
        height, width = self._base.shape
        if belt is None:
            return np.ones((height, width), dtype=np.float32)
        center = width / 2.0 + belt.amplitude_fraction_of_width * width * math.sin(
            2.0 * math.pi * self._calendar.year_fraction(tick)
        )
        columns = np.arange(width, dtype=np.float32)
        offset = (columns - center + width / 2.0) % width - width / 2.0
        band = np.exp(-((offset / (belt.band_width_fraction * width)) ** 2))
        return np.repeat(band[None, :], height, axis=0).astype(np.float32) * RAIN_BELT_GAIN


def _ramp(tick: int, start: int, end: int) -> float:
    if tick <= start:
        return 0.0
    if tick >= end:
        return 1.0
    return (tick - start) / max(1, end - start)
