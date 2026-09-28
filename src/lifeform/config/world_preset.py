from __future__ import annotations

from typing import Any, Literal

from pydantic import Field

from lifeform.config.parameters import FrozenModel

FeatureKind = Literal["waterholes", "oases", "vents", "caves", "kopjes", "wadi"]
WeatherProfile = Literal["temperate", "tropical_wet_dry", "arid", "boreal", "rainforest", "volcanic", "constant"]


class GridConfig(FrozenModel):
    width: int = 160
    height: int = 160


class CalendarConfig(FrozenModel):
    ticks_per_day: int = 12
    days_per_season: int = 12
    season_names: tuple[str, ...] = ("spring", "summer", "autumn", "winter")
    days_per_lunar_cycle: int = 8


class FeatureStamp(FrozenModel):
    kind: FeatureKind
    count: int = 1
    min_radius: int = 2
    max_radius: int = 4


class TerrainConfig(FrozenModel):
    water_fraction: float = 0.08
    lattice_cells: int = 5
    octaves: int = 5
    persistence: float = 0.5
    mountain_strength: float = 0.3
    ridge_strength: float = 0.0
    max_elevation_m: float = 800.0
    moisture_base: float = 0.5
    moisture_water_reach_patches: float = 12.0
    river_threshold_fraction: float = 0.004
    deep_water_depth_fraction: float = 0.35
    rock_elevation_fraction: float = 0.92
    feature_stamps: tuple[FeatureStamp, ...] = ()


class RainBelt(FrozenModel):
    amplitude_fraction_of_width: float = 0.35
    band_width_fraction: float = 0.2


class ClimateDrift(FrozenModel):
    total_c: float
    start_tick: int
    end_tick: int


class RegionalDrift(FrozenModel):
    band: Literal["inner", "outer"]
    temperature_c: float = 0.0
    precipitation_factor: float = 1.0
    start_tick: int
    end_tick: int


class ClimateConfig(FrozenModel):
    equator_temperature_c: float = 24.0
    latitudinal_range_c: float = 10.0
    seasonal_amplitude_c: float = 6.0
    diurnal_amplitude_c: float = 6.0
    lapse_rate_c_per_km: float = 6.5
    anomaly_sigma_c: float = 0.4
    anomaly_persistence: float = 0.97
    day_length_amplitude_hours: float = 2.0
    weather_profile: WeatherProfile = "temperate"
    rain_mm_per_tick: float = 2.0
    wind_speed: float = 0.5
    prevailing_wind_degrees: float = 270.0
    rain_belt: RainBelt | None = None
    tidally_locked: bool = False
    day_side_temperature_c: float = 60.0
    night_side_temperature_c: float = -50.0
    drift: ClimateDrift | None = None
    regional_drifts: tuple[RegionalDrift, ...] = ()


class ScheduledEruption(FrozenModel):
    tick: int
    lava_radius: int = 6
    ash_radius: int = 25


class ScheduledDrought(FrozenModel):
    tick: int
    duration_ticks: int = 144
    precipitation_factor: float = 0.2


class RiftConfig(FrozenModel):
    open_tick: int
    duration_ticks: int = 100
    channel_width: int = 3


class FloodPulseConfig(FrozenModel):
    amplitude_m: float = 1.2
    peak_year_fraction: float = 0.6
    floodplain_elevation_fraction: float = 0.08


class EpidemicConfig(FrozenModel):
    tick: int
    transmission: float = 0.12
    virulence: float = 0.02
    latent_ticks: float = 12.0
    infectious_ticks: float = 36.0
    immunity_ticks: float = 400.0
    environmental_shedding: float = 0.05
    environmental_half_life_ticks: float = 24.0
    host_distance: float = 0.3


class DisturbanceConfig(FrozenModel):
    lightning_fire_probability: float = 0.0
    fire_spread_probability: float = 0.35
    fire_burn_ticks: int = 2
    fire_damage_per_tick: float = 0.4
    eruption_rate_per_tick: float = 0.0
    eruptions: tuple[ScheduledEruption, ...] = ()
    droughts: tuple[ScheduledDrought, ...] = ()
    rift: RiftConfig | None = None
    flood_pulse: FloodPulseConfig | None = None
    epidemic: EpidemicConfig | None = None
    rafting_probability: float = 0.0


class FounderGroup(FrozenModel):
    archetype: str
    count: int
    groups: int = 1
    overrides: dict[str, float] = Field(default_factory=dict)
    name: str | None = None


class PopulationTargets(FrozenModel):
    herbivores: int = 80
    predators: int = 10
    max_population: int = 300


class WorldPreset(FrozenModel):
    slug: str
    title: str
    biome: str
    description: str
    question: str
    palette: str
    default_ticks: int = 1500
    grid: GridConfig = GridConfig()
    calendar: CalendarConfig = CalendarConfig()
    terrain: TerrainConfig = TerrainConfig()
    climate: ClimateConfig = ClimateConfig()
    disturbances: DisturbanceConfig = DisturbanceConfig()
    founders: tuple[FounderGroup, ...]
    targets: PopulationTargets = PopulationTargets()
    productivity_scale: float | Literal["calibrated"] = "calibrated"
    ecology: dict[str, Any] = Field(default_factory=dict)
    stretch: bool = False

    @property
    def founder_count(self) -> int:
        return sum(group.count for group in self.founders)
