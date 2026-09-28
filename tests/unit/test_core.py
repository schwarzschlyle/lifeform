from __future__ import annotations

import numpy as np
from hypothesis import given
from hypothesis import strategies as st

from lifeform.core.geometry import Direction, Position, TorusMetric
from lifeform.core.time import Calendar
from lifeform.world.field_math import advect, diffuse

coordinate = st.integers(min_value=0, max_value=63)


@given(coordinate, coordinate, coordinate, coordinate)
def test_torus_distance_is_symmetric_and_bounded(x1: int, y1: int, x2: int, y2: int) -> None:
    metric = TorusMetric(64, 64)
    first, second = Position(x1, y1), Position(x2, y2)
    assert metric.distance(first, second) == metric.distance(second, first)
    dx, dy = metric.delta(first, second)
    assert abs(dx) <= 32
    assert abs(dy) <= 32


def test_walking_off_an_edge_wraps_around() -> None:
    metric = TorusMetric(10, 10)
    assert metric.step(Position(9, 0), Direction.NORTH_EAST) == Position(0, 9)
    assert metric.steps(Position(0, 0), Position(9, 9)) == 1


def test_direction_from_offset_points_the_right_way() -> None:
    assert Direction.from_offset(0, -1) == Direction.NORTH
    assert Direction.from_offset(1, 1) == Direction.SOUTH_EAST
    assert Direction.WEST.opposite == Direction.EAST


def test_season_words_do_not_repeat_the_stage() -> None:
    tropical = Calendar(12, 12, ("early wet", "late wet", "early dry", "late dry"), 8)
    temperate = Calendar(12, 12, ("spring", "summer", "autumn", "winter"), 8)
    assert tropical.season_word(0) == "early wet"
    assert temperate.season_word(0) == "early spring"
    assert temperate.day_phase_word(6) == "midday"


@given(st.floats(min_value=0.0, max_value=0.25))
def test_diffusion_conserves_mass(rate: float) -> None:
    grid = np.random.default_rng(1).random((16, 16)).astype(np.float32)
    assert np.isclose(diffuse(grid, rate).sum(), grid.sum(), rtol=1e-4)


@given(st.floats(min_value=-3.0, max_value=3.0), st.floats(min_value=-3.0, max_value=3.0))
def test_advection_conserves_mass(shift_x: float, shift_y: float) -> None:
    grid = np.random.default_rng(2).random((16, 16)).astype(np.float32)
    assert np.isclose(advect(grid, shift_x, shift_y).sum(), grid.sum(), rtol=1e-4)
