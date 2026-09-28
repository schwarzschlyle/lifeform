from __future__ import annotations

import asyncio
import time
from collections.abc import Mapping
from typing import Any

import httpx2
from typesafe_sdk import (
    AsyncTypeSafeClient,
    Choice,
    RetryPolicy,
    Score,
    SystemOneResponse,
    TypeSafeAPIConnectionError,
    TypeSafeAPIError,
    TypeSafeAuthenticationError,
    TypeSafeError,
    TypeSafePermissionDeniedError,
    TypeSafeRateLimitError,
)

from lifeform.adapters.system_one.rate_governor import RateGovernor
from lifeform.cognition.brain import BrainMisuse, BrainUnavailable
from lifeform.config.brains import SystemOneSettings

RETRYABLE_STATUSES = frozenset({408, 409, 425, 429, 500, 502, 503, 504})
BACKOFF_INITIAL_SECONDS = 0.5
BACKOFF_MAX_SECONDS = 8.0
MILLISECONDS = 1000.0
PROBE_STATE = {"task": "A connectivity check.", "you": "a small animal", "here": "open grassland"}
PROBE_TOKENS = 100


class SystemOneGateway:
    """Talks to one System One endpoint (Jev or a compatible model) through the official TypeSafe SDK."""

    def __init__(
        self,
        settings: SystemOneSettings,
        api_key: str,
        governor: RateGovernor,
        transport: httpx2.AsyncBaseTransport | None = None,
    ) -> None:
        self._settings = settings
        self._governor = governor
        self._semaphore = asyncio.Semaphore(settings.max_in_flight)
        try:
            self._client = AsyncTypeSafeClient(
                api_key=api_key,
                base_url=settings.base_url,
                model=settings.model,
                retry=RetryPolicy(max_retries=0),
                timeout=settings.request_timeout_seconds,
                transport=transport,
            )
        except TypeSafeError as error:
            raise BrainMisuse(f"could not create the {settings.title} client: {error}") from error

    async def ask(
        self, state: Mapping[str, Any], questions: Mapping[str, Choice | Score], estimated_tokens: int
    ) -> tuple[SystemOneResponse, float, int]:
        started = time.perf_counter()
        deadline = started + self._settings.retry_budget_seconds
        attempts = 0
        backoff = BACKOFF_INITIAL_SECONDS
        while True:
            attempts += 1
            await self._governor.acquire(estimated_tokens)
            try:
                async with self._semaphore:
                    response = await self._client.system_one(dict(state), dict(questions), model=self._settings.model)
                return response, (time.perf_counter() - started) * MILLISECONDS, attempts
            except TypeSafeRateLimitError:
                self._governor.on_rate_limited()
            except (TypeSafeAuthenticationError, TypeSafePermissionDeniedError) as error:
                raise BrainMisuse(
                    f"{self._settings.title} rejected the API key (set ${self._settings.api_key_env}): {error}"
                ) from error
            except TypeSafeAPIError as error:
                if error.status not in RETRYABLE_STATUSES:
                    raise BrainMisuse(
                        f"{self._settings.title} rejected the request ({error.status}): {error}"
                    ) from error
            except TypeSafeAPIConnectionError:
                pass
            if attempts > self._settings.max_retries or time.perf_counter() + backoff > deadline:
                raise BrainUnavailable(
                    f"{self._settings.title} unavailable at {self._settings.base_url} after {attempts} attempts"
                )
            await asyncio.sleep(backoff)
            backoff = min(BACKOFF_MAX_SECONDS, backoff * 2.0)

    async def probe_latency_ms(self) -> float:
        question = Choice(instructions="Which option fits this animal?", criteria={"graze": None, "rest": None})
        _, latency_ms, _ = await self.ask(PROBE_STATE, {"action": question}, PROBE_TOKENS)
        return latency_ms

    async def model_cards(self) -> dict[str, str]:
        try:
            listing = await self._client.models.list()
        except TypeSafeError as error:
            raise BrainUnavailable(
                f"could not list {self._settings.title} models at {self._settings.base_url}: {error}"
            ) from error
        return {model.name: model.description for model in listing.models}

    async def close(self) -> None:
        await self._client.aclose()
