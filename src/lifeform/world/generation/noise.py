from __future__ import annotations

import numpy as np

from lifeform.world.field_math import FloatGrid


class PeriodicNoise:
    """Value noise on a wrapping lattice, so every field tiles seamlessly on the torus."""

    def __init__(self, height: int, width: int, rng: np.random.Generator) -> None:
        self._height = height
        self._width = width
        self._rng = rng

    def octave(self, cells: int) -> FloatGrid:
        cells_y = max(1, round(cells * self._height / max(self._height, self._width)))
        cells_x = max(1, round(cells * self._width / max(self._height, self._width)))
        lattice = self._rng.random((cells_y, cells_x))
        row_low, row_high, row_blend = self._axis(self._height, cells_y)
        column_low, column_high, column_blend = self._axis(self._width, cells_x)
        top = self._lerp(lattice[np.ix_(row_low, column_low)], lattice[np.ix_(row_low, column_high)], column_blend)
        bottom = self._lerp(lattice[np.ix_(row_high, column_low)], lattice[np.ix_(row_high, column_high)], column_blend)
        return self._lerp(top, bottom, row_blend[:, None]).astype(np.float32)

    def fractal(self, cells: int, octaves: int, persistence: float) -> FloatGrid:
        total = np.zeros((self._height, self._width), dtype=np.float32)
        amplitude = 1.0
        for level in range(octaves):
            total += amplitude * self.octave(cells * 2**level)
            amplitude *= persistence
        return normalized(total)

    @staticmethod
    def _axis(extent: int, cells: int) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
        coordinate = np.arange(extent) * cells / extent
        low = np.floor(coordinate).astype(int) % cells
        high = (low + 1) % cells
        fraction = coordinate - np.floor(coordinate)
        return low, high, fraction * fraction * (3.0 - 2.0 * fraction)

    @staticmethod
    def _lerp(start: np.ndarray, end: np.ndarray, weight: np.ndarray) -> np.ndarray:
        return start + (end - start) * weight


def normalized(grid: np.ndarray) -> FloatGrid:
    low, high = float(grid.min()), float(grid.max())
    if high - low < 1e-9:
        return np.zeros_like(grid, dtype=np.float32)
    return ((grid - low) / (high - low)).astype(np.float32)
