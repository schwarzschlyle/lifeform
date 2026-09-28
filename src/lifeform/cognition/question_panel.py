from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from lifeform.actions.calls import CALL_SPECS, Call
from lifeform.biology.organism import Organism
from lifeform.cognition.affordances import Affordance

PANEL_VERSION = "panel-1"
NOTHING_IN_PARTICULAR = "nothing_in_particular"
YOUNG_CALLS = (Call.SILENT, Call.CONTACT, Call.DISTRESS)

EFFORT_INSTRUCTIONS = "How much physical effort does this animal's situation call for right now?"
EFFORT_LEVELS: tuple[str, ...] = (
    "minimal: nothing is pressing; save energy",
    "steady: an ordinary, sustainable pace",
    "hurried: something needs doing soon and is worth extra energy",
    "all-out: life or death right now; a maximum burst",
)
THREAT_INSTRUCTIONS = "How much danger is this animal in right now?"
THREAT_LEVELS: tuple[str, ...] = (
    "none: nothing threatening is sensed",
    "low: a possible threat, distant or unclear",
    "moderate: a real threat is present but not close, or not focused on this animal",
    "high: a dangerous animal or hazard is close or coming closer",
    "deadly: it is being attacked or is about to be",
)
CALL_INSTRUCTIONS = "Which call does this animal make now?"
FOCUS_INSTRUCTIONS = "Which single thing around this animal matters most to it right now?"


def action_instructions(hours_per_tick: float) -> str:
    hours = "hour" if hours_per_tick == 1 else f"{hours_per_tick:g} hours"
    return (
        f"Choose the one option this animal takes during the next {hours}. Like a real wild animal, it acts on "
        "its strongest feelings, its temperament and instincts, and what it senses and remembers, in order to "
        "stay alive, stay well, raise its young and breed."
    )


@dataclass(frozen=True, slots=True)
class ChoiceQuestion:
    instructions: str
    criteria: dict[str, str]


@dataclass(frozen=True, slots=True)
class ScoreQuestion:
    instructions: str
    levels: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class QuestionPanel:
    version: str
    menu: tuple[Affordance, ...]
    calls: tuple[Call, ...]
    action: ChoiceQuestion
    effort: ScoreQuestion
    threat: ScoreQuestion
    call: ChoiceQuestion
    focus: ChoiceQuestion

    def affordance(self, key: str) -> Affordance | None:
        for affordance in self.menu:
            if affordance.key == key:
                return affordance
        return None


class QuestionPanelBuilder:
    def __init__(self, hours_per_tick: float, rng: np.random.Generator) -> None:
        self._action_instructions = action_instructions(hours_per_tick)
        self._rng = rng

    def build(self, organism: Organism, menu: list[Affordance], focus_options: dict[str, str]) -> QuestionPanel:
        order = self._rng.permutation(len(menu))
        presented = tuple(menu[int(index)] for index in order)
        calls = self.legal_calls(organism)
        focus = {**focus_options, NOTHING_IN_PARTICULAR: "nothing stands out"}
        return QuestionPanel(
            version=PANEL_VERSION,
            menu=presented,
            calls=calls,
            action=ChoiceQuestion(
                self._action_instructions, {affordance.key: affordance.description for affordance in presented}
            ),
            effort=ScoreQuestion(EFFORT_INSTRUCTIONS, EFFORT_LEVELS),
            threat=ScoreQuestion(THREAT_INSTRUCTIONS, THREAT_LEVELS),
            call=ChoiceQuestion(CALL_INSTRUCTIONS, {call.value: CALL_SPECS[call].description for call in calls}),
            focus=ChoiceQuestion(FOCUS_INSTRUCTIONS, focus),
        )

    @staticmethod
    def legal_calls(organism: Organism) -> tuple[Call, ...]:
        vocal = organism.trait("vocal_capacity")
        legal: list[Call] = []
        for call, spec in CALL_SPECS.items():
            if not organism.is_adult and call not in YOUNG_CALLS:
                continue
            if spec.adults_only and not organism.is_adult:
                continue
            if vocal >= spec.min_vocal_capacity:
                legal.append(call)
        return tuple(legal)
