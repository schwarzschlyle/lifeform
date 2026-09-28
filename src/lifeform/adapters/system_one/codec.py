from __future__ import annotations

from typesafe_sdk import Choice, Score, SystemOneResponse

from lifeform.cognition.brain import BrainMisuse
from lifeform.cognition.decision import ChoiceResult, RawDecision, ScoreResult
from lifeform.cognition.mind_state import MindState
from lifeform.cognition.question_panel import ChoiceQuestion, QuestionPanel, ScoreQuestion

QUESTION_KEYS: tuple[str, ...] = ("action", "effort", "threat", "call", "focus")
PANEL_OVERHEAD_TOKENS = 250
TOKENS_PER_OPTION = 18


class PanelCodec:
    """The only place where Lifeform's question panel meets TypeSafe SDK types."""

    def questions(self, panel: QuestionPanel) -> dict[str, Choice | Score]:
        return {
            "action": self._choice(panel.action),
            "effort": self._score(panel.effort),
            "threat": self._score(panel.threat),
            "call": self._choice(panel.call),
            "focus": self._choice(panel.focus),
        }

    @staticmethod
    def estimated_tokens(mind: MindState, panel: QuestionPanel) -> int:
        options = len(panel.menu) + len(panel.calls) + len(panel.focus.criteria)
        return mind.estimated_tokens + PANEL_OVERHEAD_TOKENS + TOKENS_PER_OPTION * options

    def decode(self, organism_id: int, response: SystemOneResponse, latency_ms: float, attempts: int) -> RawDecision:
        missing = [key for key in QUESTION_KEYS if key not in response.answers]
        if missing:
            raise BrainMisuse(f"Jev response is missing answers: {missing}")
        choices = response.choices
        scores = response.scores
        return RawDecision(
            organism_id=organism_id,
            action=self._choice_result(
                choices["action"].choice, choices["action"].confidence, dict(choices["action"].probabilities)
            ),
            effort=ScoreResult(
                scores["effort"].score, scores["effort"].confidence, dict(scores["effort"].probabilities)
            ),
            threat=ScoreResult(
                scores["threat"].score, scores["threat"].confidence, dict(scores["threat"].probabilities)
            ),
            call=self._choice_result(
                choices["call"].choice, choices["call"].confidence, dict(choices["call"].probabilities)
            ),
            focus=self._choice_result(
                choices["focus"].choice, choices["focus"].confidence, dict(choices["focus"].probabilities)
            ),
            model=response.model,
            input_tokens=response.usage.input_tokens or 0,
            latency_ms=latency_ms,
            attempts=attempts,
        )

    @staticmethod
    def _choice(question: ChoiceQuestion) -> Choice:
        return Choice(instructions=question.instructions, criteria=dict(question.criteria))

    @staticmethod
    def _score(question: ScoreQuestion) -> Score:
        return Score(instructions=question.instructions, criteria=list(question.levels))

    @staticmethod
    def _choice_result(choice: str, confidence: float, probabilities: dict[str, float]) -> ChoiceResult:
        return ChoiceResult(choice, confidence, probabilities)
