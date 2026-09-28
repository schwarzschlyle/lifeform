from __future__ import annotations

import time
from collections.abc import Callable
from dataclasses import dataclass

from lifeform.config.brains import SystemOneSettings
from lifeform.config.world_preset import WorldPreset

DEFAULT_TOKENS_PER_CALL = 1300
SECONDS_PER_HOUR = 3600.0
MINUTES_PER_HOUR = 60.0
MILLION = 1_000_000.0
MIN_FOUNDERS_PER_GROUP = 2


@dataclass(frozen=True, slots=True)
class WorldEstimate:
    slug: str
    title: str
    ticks: int
    founders: int
    expected_mean_organisms: float
    ceiling_organisms: int
    expected_calls: int
    ceiling_calls: int

    def expected_usd(self, tokens_per_call: int, price: float) -> float:
        return self.expected_calls * tokens_per_call * price / MILLION

    def ceiling_usd(self, tokens_per_call: int, price: float) -> float:
        return self.ceiling_calls * tokens_per_call * price / MILLION


@dataclass(frozen=True, slots=True)
class RunEstimate:
    worlds: tuple[WorldEstimate, ...]
    tokens_per_call: int
    price_per_million: float
    requests_per_minute: float
    host_usd_per_hour: float = 0.0

    @property
    def expected_calls(self) -> int:
        return sum(world.expected_calls for world in self.worlds)

    @property
    def ceiling_calls(self) -> int:
        return sum(world.ceiling_calls for world in self.worlds)

    @property
    def expected_token_usd(self) -> float:
        return self.expected_calls * self.tokens_per_call * self.price_per_million / MILLION

    @property
    def expected_hosting_usd(self) -> float:
        return self.expected_hours * self.host_usd_per_hour

    @property
    def expected_usd(self) -> float:
        return self.expected_token_usd + self.expected_hosting_usd

    @property
    def ceiling_usd(self) -> float:
        token_usd = self.ceiling_calls * self.tokens_per_call * self.price_per_million / MILLION
        return token_usd + self._hours_for(self.ceiling_calls) * self.host_usd_per_hour

    @property
    def expected_hours(self) -> float:
        return self._hours_for(self.expected_calls)

    @property
    def expected_tokens(self) -> int:
        return self.expected_calls * self.tokens_per_call

    def _hours_for(self, calls: int) -> float:
        return calls / max(self.requests_per_minute, 1e-9) / MINUTES_PER_HOUR


class CostEstimator:
    def __init__(self, settings: SystemOneSettings, tokens_per_call: int = DEFAULT_TOKENS_PER_CALL) -> None:
        self._settings = settings
        self._tokens_per_call = tokens_per_call

    def estimate(self, presets: list[WorldPreset], ticks: int | None, population_scale: float) -> RunEstimate:
        settings = self._settings
        worlds = tuple(self._world(preset, ticks or preset.default_ticks, population_scale) for preset in presets)
        rate = settings.requests_per_minute * settings.governor_start_fraction
        return RunEstimate(
            worlds,
            self._tokens_per_call,
            settings.price_usd_per_million_input_tokens,
            rate,
            settings.host_usd_per_hour,
        )

    @staticmethod
    def _world(preset: WorldPreset, ticks: int, population_scale: float) -> WorldEstimate:
        founders = sum(max(MIN_FOUNDERS_PER_GROUP, round(group.count * population_scale)) for group in preset.founders)
        target = (preset.targets.herbivores + preset.targets.predators) * population_scale
        expected_mean = max(float(founders), 0.5 * (founders + target))
        ceiling = max(founders, round(preset.targets.max_population * population_scale))
        return WorldEstimate(
            preset.slug,
            preset.title,
            ticks,
            founders,
            expected_mean,
            ceiling,
            round(expected_mean * ticks),
            ceiling * ticks,
        )


class BudgetGuard:
    """Stops a run before it spends more than allowed: per-token charges plus hourly hosting while it runs."""

    def __init__(
        self,
        max_usd: float | None,
        max_calls: int | None,
        price_per_million: float,
        host_usd_per_hour: float = 0.0,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self._max_usd = max_usd
        self._max_calls = max_calls
        self._price = price_per_million
        self._host_rate = host_usd_per_hour
        self._clock = clock
        self._started = clock()
        self.calls = 0
        self.tokens = 0

    @property
    def token_usd(self) -> float:
        return self.tokens * self._price / MILLION

    @property
    def hosting_usd(self) -> float:
        return (self._clock() - self._started) / SECONDS_PER_HOUR * self._host_rate

    @property
    def spent_usd(self) -> float:
        return self.token_usd + self.hosting_usd

    def record(self, calls: int, tokens: int) -> None:
        self.calls += calls
        self.tokens += tokens

    def can_afford(self, upcoming_calls: int, tokens_per_call: int) -> bool:
        if self._max_calls is not None and self.calls + upcoming_calls > self._max_calls:
            return False
        if self._max_usd is None:
            return True
        projected = self.spent_usd + upcoming_calls * tokens_per_call * self._price / MILLION
        return projected <= self._max_usd
