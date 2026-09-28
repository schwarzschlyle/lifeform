from __future__ import annotations

import asyncio
import time
from collections.abc import Callable
from dataclasses import dataclass, field

SECONDS_PER_MINUTE = 60.0
MIN_RATE_FRACTION = 0.05
RECOVERY_STEP_FRACTION = 0.05
RECOVERY_WINDOW_SECONDS = 60.0
REQUEST_BURST = 20.0


@dataclass(slots=True)
class TokenBucket:
    capacity: float
    refill_per_second: float
    clock: Callable[[], float]
    tokens: float = field(init=False)
    updated: float = field(init=False)

    def __post_init__(self) -> None:
        self.tokens = self.capacity
        self.updated = self.clock()

    def wait_seconds(self, amount: float) -> float:
        self._refill()
        if self.tokens >= amount:
            return 0.0
        return (amount - self.tokens) / max(self.refill_per_second, 1e-9)

    def take(self, amount: float) -> None:
        self._refill()
        self.tokens -= amount

    def _refill(self) -> None:
        now = self.clock()
        self.tokens = min(self.capacity, self.tokens + (now - self.updated) * self.refill_per_second)
        self.updated = now


class RateGovernor:
    """Shared request and token budget across every world, with additive-increase / multiplicative-decrease."""

    def __init__(
        self,
        requests_per_minute: int,
        tokens_per_second: int,
        start_fraction: float,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self._limit_rps = requests_per_minute / SECONDS_PER_MINUTE
        self._limit_tps = float(tokens_per_second)
        self._fraction = start_fraction
        self._ceiling_fraction = start_fraction
        self._clock = clock
        self._requests = TokenBucket(REQUEST_BURST, self._limit_rps * start_fraction, clock)
        self._tokens = TokenBucket(self._limit_tps, self._limit_tps * start_fraction, clock)
        self._lock = asyncio.Lock()
        self._last_throttle = clock()
        self.throttle_events = 0

    @property
    def requests_per_minute(self) -> float:
        return self._requests.refill_per_second * SECONDS_PER_MINUTE

    async def acquire(self, estimated_tokens: int) -> None:
        async with self._lock:
            while True:
                wait = max(self._requests.wait_seconds(1.0), self._tokens.wait_seconds(float(estimated_tokens)))
                if wait <= 0.0:
                    break
                await asyncio.sleep(wait)
            self._requests.take(1.0)
            self._tokens.take(float(estimated_tokens))
            self._recover()

    def on_rate_limited(self) -> None:
        self.throttle_events += 1
        self._last_throttle = self._clock()
        self._set_fraction(max(MIN_RATE_FRACTION, self._fraction / 2.0))

    def _recover(self) -> None:
        if self._fraction >= self._ceiling_fraction:
            return
        if self._clock() - self._last_throttle >= RECOVERY_WINDOW_SECONDS:
            self._last_throttle = self._clock()
            self._set_fraction(min(self._ceiling_fraction, self._fraction + RECOVERY_STEP_FRACTION))

    def _set_fraction(self, fraction: float) -> None:
        self._fraction = fraction
        self._requests.refill_per_second = self._limit_rps * fraction
        self._tokens.refill_per_second = self._limit_tps * fraction
