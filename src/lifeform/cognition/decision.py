from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from lifeform.actions.calls import Call
from lifeform.cognition.affordances import Affordance


class DecisionStatus(StrEnum):
    OK = "ok"
    STALLED = "stalled"


class Band(StrEnum):
    DECISIVE = "decisive"
    HESITANT = "hesitant"
    DITHERING = "dithering"


@dataclass(frozen=True, slots=True)
class ChoiceResult:
    choice: str
    confidence: float
    probabilities: dict[str, float]


@dataclass(frozen=True, slots=True)
class ScoreResult:
    score: float
    confidence: float
    probabilities: dict[int, float]


@dataclass(frozen=True, slots=True)
class RawDecision:
    organism_id: int
    action: ChoiceResult
    effort: ScoreResult
    threat: ScoreResult
    call: ChoiceResult
    focus: ChoiceResult
    model: str
    input_tokens: int
    latency_ms: float
    attempts: int
    status: DecisionStatus = DecisionStatus.OK


@dataclass(frozen=True, slots=True)
class Intent:
    organism_id: int
    affordance: Affordance
    effort: int
    band: Band
    urgent: bool
    call: Call
    focus_label: str | None
    threat_score: float
    sampled_key: str
    argmax_key: str
    confidence: float
    stalled: bool = False

    @property
    def exploratory(self) -> bool:
        return self.sampled_key != self.argmax_key
