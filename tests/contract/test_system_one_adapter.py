from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

import httpx2
import pytest

from lifeform.adapters.system_one.brain import SystemOneBrain
from lifeform.adapters.system_one.codec import QUESTION_KEYS, PanelCodec
from lifeform.adapters.system_one.gateway import SystemOneGateway
from lifeform.adapters.system_one.rate_governor import RateGovernor
from lifeform.cognition.brain import BrainMisuse
from lifeform.config.brains import UNAUTHENTICATED_KEY, BrainLibrary, SystemOneSettings
from lifeform.simulation.engine import Simulation
from lifeform.simulation.phases.deliberation import DeliberationOptions
from lifeform.simulation.world_factory import BuiltWorld

TOO_MANY_REQUESTS = 429
UNAUTHORIZED = 401


def synthetic_answer(question: dict[str, Any]) -> dict[str, Any]:
    if question["type"] == "choice":
        keys = list(question["criteria"])
        probabilities = {key: (0.6 if index == 0 else 0.4 / max(1, len(keys) - 1)) for index, key in enumerate(keys)}
        return {"type": "choice", "choice": keys[0], "confidence": 0.7, "probabilities": probabilities}
    levels = question["criteria"]
    probabilities = {str(index): 1.0 / len(levels) for index in range(len(levels))}
    return {
        "type": "score",
        "score": (len(levels) - 1) / 2,
        "confidence": 0.3,
        "legend": {str(index): level for index, level in enumerate(levels)},
        "probabilities": probabilities,
    }


ROOT = Path(__file__).resolve().parents[2]


class FakeSystemOne:
    """Answers like any System One server (Jev or Kev) and records what it was sent."""

    def __init__(self, throttle_first: int = 0, status: int = 200) -> None:
        self.requests: list[dict[str, Any]] = []
        self.headers: list[httpx2.Headers] = []
        self.urls: list[str] = []
        self._throttle_first = throttle_first
        self._status = status

    def __call__(self, request: httpx2.Request) -> httpx2.Response:
        body = json.loads(request.content)
        self.urls.append(str(request.url))
        self.requests.append(body)
        self.headers.append(request.headers)
        if self._status != 200:
            return httpx2.Response(self._status, json={"detail": "denied"})
        if len(self.requests) <= self._throttle_first:
            return httpx2.Response(TOO_MANY_REQUESTS, json={"detail": "slow down"}, headers={"retry-after-ms": "1"})
        answers = {name: synthetic_answer(question) for name, question in body["questions"].items()}
        return httpx2.Response(
            200, json={"model": body["model"], "answers": answers, "usage": {"input_tokens": 1234, "output_tokens": 5}}
        )


def brain_with(
    fake: FakeSystemOne, settings: SystemOneSettings | None = None, api_key: str = "test-key"
) -> SystemOneBrain:
    chosen = settings or SystemOneSettings()
    governor = RateGovernor(chosen.requests_per_minute, chosen.tokens_per_second, chosen.governor_start_fraction)
    gateway = SystemOneGateway(chosen, api_key, governor, transport=httpx2.MockTransport(fake))
    return SystemOneBrain(chosen, gateway, PanelCodec())


@pytest.mark.asyncio
async def test_one_real_sdk_request_per_animal_with_all_five_questions(small_world: BuiltWorld) -> None:
    fake = FakeSystemOne()
    brain = brain_with(fake)
    simulation = Simulation(small_world, brain, DeliberationOptions())
    population = len(simulation.population)
    context = await simulation.advance()
    await brain.close()
    assert len(fake.requests) == population
    request = fake.requests[0]
    assert set(request["questions"]) == set(QUESTION_KEYS)
    assert request["model"] == "jev-1.13.0"
    assert fake.urls[0].startswith("https://api.typesafe.ai/")
    assert fake.headers[0]["authorization"] == "Bearer test-key"
    decision = next(iter(context.decisions.values()))
    assert decision.input_tokens == 1234
    assert decision.model == "jev-1.13.0"
    assert 0.0 <= decision.action.confidence <= 1.0


@pytest.mark.asyncio
async def test_rate_limits_are_retried_not_substituted(small_world: BuiltWorld) -> None:
    fake = FakeSystemOne(throttle_first=1)
    brain = brain_with(fake)
    simulation = Simulation(small_world, brain, DeliberationOptions())
    population = len(simulation.population)
    context = await simulation.advance()
    await brain.close()
    assert len(context.decisions) == population
    assert len(fake.requests) == population + 1


@pytest.mark.asyncio
async def test_a_rejected_key_fails_fast(small_world: BuiltWorld) -> None:
    brain = brain_with(FakeSystemOne(status=UNAUTHORIZED))
    simulation = Simulation(small_world, brain, DeliberationOptions())
    with pytest.raises(BrainMisuse):
        await simulation.advance()
    await brain.close()


@pytest.mark.asyncio
async def test_switching_to_kev_sends_the_same_calls_to_the_kev_server(small_world: BuiltWorld) -> None:
    kev = BrainLibrary(ROOT / "brains.yaml").load().provider("kev")
    fake = FakeSystemOne()
    brain = brain_with(fake, kev, UNAUTHENTICATED_KEY)
    simulation = Simulation(small_world, brain, DeliberationOptions())
    population = len(simulation.population)
    context = await simulation.advance()
    await brain.close()
    assert brain.name == "kev"
    assert len(fake.requests) == population
    assert fake.urls[0].startswith(f"{kev.base_url}/")
    assert fake.requests[0]["model"] == "kev-latest"
    assert set(fake.requests[0]["questions"]) == set(QUESTION_KEYS)
    assert next(iter(context.decisions.values())).model == "kev-latest"


@pytest.mark.live
@pytest.mark.asyncio
@pytest.mark.skipif(not os.environ.get("TYPESAFE_API_KEY"), reason="needs TYPESAFE_API_KEY")
async def test_live_jev_answers_one_tick(small_world: BuiltWorld) -> None:
    brain = brain_with_live_key(os.environ["TYPESAFE_API_KEY"])
    simulation = Simulation(small_world, brain, DeliberationOptions())
    context = await simulation.advance()
    await brain.close()
    assert len(context.decisions) == len(context.minds)


def brain_with_live_key(api_key: str) -> SystemOneBrain:
    settings = SystemOneSettings()
    governor = RateGovernor(settings.requests_per_minute, settings.tokens_per_second, settings.governor_start_fraction)
    return SystemOneBrain(settings, SystemOneGateway(settings, api_key, governor), PanelCodec())
