from __future__ import annotations

from lifeform.adapters.system_one.codec import PanelCodec
from lifeform.adapters.system_one.gateway import SystemOneGateway
from lifeform.cognition.decision import RawDecision
from lifeform.cognition.mind_state import MindState
from lifeform.cognition.question_panel import QuestionPanel
from lifeform.config.brains import SystemOneSettings


class SystemOneBrain:
    """Every animal's decision comes from one System One call: Jev, or a compatible model such as Kev."""

    def __init__(self, settings: SystemOneSettings, gateway: SystemOneGateway, codec: PanelCodec) -> None:
        self.name = settings.name
        self._settings = settings
        self._gateway = gateway
        self._codec = codec

    @property
    def settings(self) -> SystemOneSettings:
        return self._settings

    async def decide(self, mind: MindState, panel: QuestionPanel) -> RawDecision:
        response, latency_ms, attempts = await self._gateway.ask(
            mind.payload, self._codec.questions(panel), self._codec.estimated_tokens(mind, panel)
        )
        return self._codec.decode(mind.organism_id, response, latency_ms, attempts)

    async def served_model(self) -> str:
        cards = await self._gateway.model_cards()
        return cards.get(self._settings.model) or f"{self._settings.model} (not listed by the server)"

    async def close(self) -> None:
        await self._gateway.close()
