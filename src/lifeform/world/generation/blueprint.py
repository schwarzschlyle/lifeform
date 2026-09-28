from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from lifeform.world.field_math import FloatGrid


@dataclass(slots=True)
class WorldBlueprint:
    terrain: np.ndarray
    elevation_normalized: FloatGrid
    elevation_m: FloatGrid
    base_water: FloatGrid
    moisture: FloatGrid
    canopy: FloatGrid
    flood_mask: np.ndarray
    rift_mask: np.ndarray
    inner_band: np.ndarray
    substellar_cosine: FloatGrid
    vents: np.ndarray
    wadi: np.ndarray

    @property
    def shape(self) -> tuple[int, int]:
        return int(self.terrain.shape[0]), int(self.terrain.shape[1])
