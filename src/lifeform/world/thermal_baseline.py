from __future__ import annotations

import math

import numpy as np

from lifeform.config.world_preset import ClimateConfig
from lifeform.world.field_math import FloatGrid

TIDAL_RADIATIVE_EXPONENT = 0.25


class ThermalBaseline:
    def __init__(self, config: ClimateConfig) -> None:
        self._config = config

    def annual_mean(self, elevation_m: FloatGrid, substellar_cosine: FloatGrid) -> FloatGrid:
        config = self._config
        lapse = config.lapse_rate_c_per_km * elevation_m / 1000.0
        return (self._radiative(substellar_cosine) - lapse).astype(np.float32)

    def _radiative(self, substellar_cosine: FloatGrid) -> FloatGrid:
        config = self._config
        height, width = substellar_cosine.shape
        if config.tidally_locked:
            exposure = np.clip(substellar_cosine, 0.0, None) ** TIDAL_RADIATIVE_EXPONENT
            span = config.day_side_temperature_c - config.night_side_temperature_c
            return (config.night_side_temperature_c + span * exposure).astype(np.float32)
        rows = np.arange(height, dtype=np.float32)
        warmth = 0.5 * (1.0 + np.cos(2.0 * math.pi * (rows - height / 2.0) / height))
        profile = config.equator_temperature_c - config.latitudinal_range_c * (1.0 - warmth)
        return np.repeat(profile[:, None], width, axis=1).astype(np.float32)
