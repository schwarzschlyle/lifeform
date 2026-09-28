from __future__ import annotations

import math

import numpy as np
import numpy.typing as npt

FloatGrid = npt.NDArray[np.float32]


def laplacian(grid: FloatGrid) -> FloatGrid:
    return (
        np.roll(grid, 1, axis=0)
        + np.roll(grid, -1, axis=0)
        + np.roll(grid, 1, axis=1)
        + np.roll(grid, -1, axis=1)
        - 4.0 * grid
    ).astype(np.float32)


def diffuse(grid: FloatGrid, rate: float) -> FloatGrid:
    return (grid + rate * laplacian(grid)).astype(np.float32)


def advect(grid: FloatGrid, shift_x: float, shift_y: float) -> FloatGrid:
    whole_x, fraction_x = math.floor(shift_x), shift_x - math.floor(shift_x)
    whole_y, fraction_y = math.floor(shift_y), shift_y - math.floor(shift_y)
    base = np.roll(grid, (whole_y, whole_x), axis=(0, 1))
    right = np.roll(base, 1, axis=1)
    down = np.roll(base, 1, axis=0)
    diagonal = np.roll(right, 1, axis=0)
    blended = (
        base * (1 - fraction_x) * (1 - fraction_y)
        + right * fraction_x * (1 - fraction_y)
        + down * (1 - fraction_x) * fraction_y
        + diagonal * fraction_x * fraction_y
    )
    return blended.astype(np.float32)


def monod(value: FloatGrid | float, half_saturation: float) -> FloatGrid:
    return np.asarray(value / (value + half_saturation), dtype=np.float32)


def gaussian_response(value: FloatGrid, optimum: float, breadth: float) -> FloatGrid:
    return np.exp(-(((value - optimum) / breadth) ** 2)).astype(np.float32)


def decay_factor(half_life_ticks: float) -> float:
    return math.log(2.0) / half_life_ticks
