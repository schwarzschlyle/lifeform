from __future__ import annotations

from typing import Protocol

from lifeform.cognition.decision import RawDecision
from lifeform.cognition.mind_state import MindState
from lifeform.cognition.question_panel import QuestionPanel


class BrainUnavailable(RuntimeError):
    """The decision source is temporarily unreachable; the call may be retried."""


class BrainMisuse(RuntimeError):
    """The request itself is invalid; retrying will not help."""


class Brain(Protocol):
    name: str

    async def decide(self, mind: MindState, panel: QuestionPanel) -> RawDecision: ...

    async def close(self) -> None: ...
