from __future__ import annotations

import pytest

from lifeform.adapters.system_one.rate_governor import RateGovernor
from lifeform.config.brains import SystemOneSettings
from lifeform.config.loaders import PresetLibrary
from lifeform.simulation.budget import BudgetGuard, CostEstimator


def test_estimate_scales_with_ticks_and_population(presets: PresetLibrary) -> None:
    preset = presets.load("red-queen-pit")
    estimator = CostEstimator(SystemOneSettings(), tokens_per_call=1000)
    small = estimator.estimate([preset], ticks=100, population_scale=0.5)
    large = estimator.estimate([preset], ticks=200, population_scale=1.0)
    assert large.expected_calls > 2 * small.expected_calls
    assert small.expected_usd == pytest.approx(small.expected_calls * 1000 * 0.042 / 1e6)
    assert small.ceiling_usd >= small.expected_usd


def test_budget_guard_refuses_calls_beyond_the_limit() -> None:
    guard = BudgetGuard(max_usd=0.01, max_calls=None, price_per_million=0.042)
    assert guard.can_afford(100, 1300)
    guard.record(100_000, 200_000_000)
    assert not guard.can_afford(1, 1300)
    capped = BudgetGuard(max_usd=None, max_calls=10, price_per_million=0.042)
    assert not capped.can_afford(11, 1)


def test_hosted_brains_are_charged_by_the_hour(presets: PresetLibrary) -> None:
    hosted = SystemOneSettings(name="kev", price_usd_per_million_input_tokens=0.0, host_usd_per_hour=2.0)
    estimate = CostEstimator(hosted).estimate([presets.load("red-queen-pit")], ticks=100, population_scale=0.5)
    assert estimate.expected_token_usd == 0.0
    assert estimate.expected_usd == pytest.approx(estimate.expected_hours * 2.0)
    assert estimate.expected_usd > 0.0
    now = [0.0]
    guard = BudgetGuard(max_usd=1.0, max_calls=None, price_per_million=0.0, host_usd_per_hour=2.0, clock=lambda: now[0])
    assert guard.can_afford(1_000, 1300)
    now[0] = 1800.0
    assert guard.spent_usd == pytest.approx(1.0)
    now[0] = 1900.0
    assert not guard.can_afford(1, 1300)


def test_rate_governor_halves_on_throttle() -> None:
    now = [0.0]
    governor = RateGovernor(1200, 250_000, 1.0, clock=lambda: now[0])
    before = governor.requests_per_minute
    governor.on_rate_limited()
    assert governor.requests_per_minute == pytest.approx(before / 2)
    assert governor.throttle_events == 1
