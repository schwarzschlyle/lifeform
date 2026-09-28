from __future__ import annotations

import math
from collections.abc import Callable
from dataclasses import dataclass

from lifeform.actions.calls import Call
from lifeform.actions.verbs import Verb
from lifeform.cognition.affordances import FOOD_VERBS, Affordance, TargetKind
from lifeform.cognition.decision import ChoiceResult, RawDecision, ScoreResult
from lifeform.cognition.mind_state import MindState
from lifeform.cognition.question_panel import NOTHING_IN_PARTICULAR, QuestionPanel
from lifeform.cognition.vocabulary import FEAR, HUNGER, SLEEPINESS, THIRST, URGE_TO_MATE, Quantizer

THREAT_LEVEL_COUNT = 5
EFFORT_LEVEL_COUNT = 4
EATING_VERBS = frozenset({*FOOD_VERBS.values(), Verb.EAT_CARCASS, Verb.SUCKLE})
DANGER_VERBS = frozenset({Verb.FLEE, Verb.FIGHT_BACK, Verb.PLAY_DEAD, Verb.HIDE, Verb.CLIMB})
HUNTING_VERBS = frozenset({Verb.ATTACK, Verb.CHASE, Verb.STALK, Verb.AMBUSH})


@dataclass(frozen=True, slots=True)
class HeuristicWeights:
    temperature: float = 0.3
    eating_base: float = 2.0
    eating_hunger: float = 4.0
    drinking_base: float = 1.0
    drinking_thirst: float = 5.0
    water_seeking: float = 4.0
    food_seeking: float = 2.4
    sleeping: float = 3.0
    hunting_base: float = 1.0
    hunting_hunger: float = 3.0
    hunting_threshold: float = 0.4
    nursing: float = 2.5
    suckling: float = 3.0
    danger: float = 1.5
    distant_cue_damping: float = 0.3
    default_damping: float = 0.5
    min_food_relevance: float = 0.05
    alarm_threshold: float = 2.5
    silent_weight: float = 0.8
    other_call_weight: float = 0.1
    other_focus_weight: float = 0.2
    effort_per_threat: float = 0.6
    threat_per_danger: float = 1.5
    courting_base: float = 1.0
    wandering_share: float = 0.3
    plentiful_food_relevance: float = 0.2
    wandering_hunger: float = 0.8
    mating_base: float = 2.0
    mating_urge: float = 3.0


def _softmax(values: dict[str, float], temperature: float) -> dict[str, float]:
    peak = max(values.values())
    exponentials = {key: math.exp((value - peak) / temperature) for key, value in values.items()}
    total = sum(exponentials.values())
    return {key: value / total for key, value in exponentials.items()}


def _confidence(probabilities: dict[str, float]) -> float:
    count = len(probabilities)
    if count <= 1:
        return 1.0
    return (count * max(probabilities.values()) - 1.0) / (count - 1.0)


def _peaked(level: float, count: int) -> dict[int, float]:
    weights = {index: math.exp(-((index - level) ** 2)) for index in range(count)}
    total = sum(weights.values())
    return {index: weight / total for index, weight in weights.items()}


def _choice(probabilities: dict[str, float]) -> ChoiceResult:
    best = max(probabilities, key=probabilities.__getitem__)
    return ChoiceResult(best, _confidence(probabilities), probabilities)


def _score(level: float, count: int) -> ScoreResult:
    probabilities = _peaked(level, count)
    expected = sum(index * probability for index, probability in probabilities.items())
    return ScoreResult(expected, max(probabilities.values()), probabilities)


def _level(quantizer: Quantizer, word: str | None) -> float:
    if word is None or word not in quantizer.words:
        return 0.0
    return quantizer.words.index(word) / (len(quantizer.words) - 1)


class HeuristicBrain:
    """Development stand-in with no API calls. Runs that use it are stamped 'heuristic' and are never Jev results."""

    name = "heuristic"

    def __init__(self, weights: HeuristicWeights | None = None) -> None:
        self._weights = weights or HeuristicWeights()

    async def decide(self, mind: MindState, panel: QuestionPanel) -> RawDecision:
        feelings = mind.payload.get("feelings", {})
        hunger = _level(HUNGER, feelings.get("hunger"))
        thirst = _level(THIRST, feelings.get("thirst"))
        tiredness = _level(SLEEPINESS, feelings.get("tiredness"))
        fear = _level(FEAR, feelings.get("fear"))
        urge = _level(URGE_TO_MATE, feelings.get("urge_to_mate"))
        utilities = {
            affordance.key: self._utility(affordance, hunger, thirst, tiredness, fear, urge)
            for affordance in panel.menu
        }
        danger = max(
            (affordance.relevance for affordance in panel.menu if affordance.verb in DANGER_VERBS), default=0.0
        )
        threat_level = min(THREAT_LEVEL_COUNT - 1.0, danger * self._weights.threat_per_danger)
        effort_level = min(EFFORT_LEVEL_COUNT - 1.0, 1.0 + threat_level * self._weights.effort_per_threat)
        return RawDecision(
            organism_id=mind.organism_id,
            action=_choice(_softmax(utilities, self._weights.temperature)),
            effort=_score(effort_level, EFFORT_LEVEL_COUNT),
            threat=_score(threat_level, THREAT_LEVEL_COUNT),
            call=_choice(_softmax(self._calls(panel, threat_level), self._weights.temperature)),
            focus=_choice(_softmax(self._focus(panel), self._weights.temperature)),
            model="heuristic",
            input_tokens=0,
            latency_ms=0.0,
            attempts=1,
        )

    def _utility(
        self, affordance: Affordance, hunger: float, thirst: float, tiredness: float, fear: float, urge: float
    ) -> float:
        weights = self._weights
        verb = affordance.verb
        relevance = affordance.relevance
        if verb == Verb.MATE_WITH:
            return weights.mating_base + weights.mating_urge * urge
        if verb == Verb.COURT and urge > 0.0:
            return weights.courting_base + weights.mating_urge * urge
        if verb in EATING_VERBS and relevance > weights.min_food_relevance:
            availability = min(1.0, relevance / weights.plentiful_food_relevance)
            return (weights.eating_base + weights.eating_hunger * hunger) * availability
        if verb == Verb.MOVE:
            return weights.wandering_hunger * max(hunger, thirst) * weights.wandering_share + (
                weights.eating_hunger * relevance
            )
        if verb == Verb.SUCKLE:
            return weights.suckling + hunger
        if verb == Verb.NURSE:
            return weights.nursing
        if verb == Verb.DRINK:
            return weights.drinking_base + weights.drinking_thirst * thirst
        if verb == Verb.GO_TO_MEMORY:
            return weights.water_seeking * thirst if "water" in affordance.key else weights.food_seeking * hunger
        if verb == Verb.SLEEP:
            return weights.sleeping * tiredness * (1.0 - fear)
        if verb in HUNTING_VERBS and hunger > weights.hunting_threshold and relevance > 0.0:
            return weights.hunting_base + weights.hunting_hunger * relevance
        if verb in DANGER_VERBS:
            distant_cue = affordance.target_kind in (TargetKind.SOUND, TargetKind.SCENT)
            return relevance * weights.danger * (weights.distant_cue_damping if distant_cue else 1.0)
        return relevance * weights.default_damping

    def _calls(self, panel: QuestionPanel, threat_level: float) -> dict[str, float]:
        weights = self._weights
        calls = {call.value: weights.other_call_weight for call in panel.calls}
        calls[Call.SILENT.value] = weights.silent_weight
        if Call.ALARM.value in calls and threat_level >= weights.alarm_threshold:
            calls[Call.ALARM.value] = 1.0
        return calls

    def _focus(self, panel: QuestionPanel) -> dict[str, float]:
        focus = dict.fromkeys(panel.focus.criteria, self._weights.other_focus_weight)
        first = next((key for key in panel.focus.criteria if key != NOTHING_IN_PARTICULAR), NOTHING_IN_PARTICULAR)
        focus[first] = 1.0
        return focus

    async def close(self) -> None:
        return None


class ScriptedBrain:
    """Test double that answers with a caller-supplied rule."""

    name = "scripted"

    def __init__(self, choose: Callable[[MindState, QuestionPanel], str]) -> None:
        self._choose = choose
        self.calls = 0

    async def decide(self, mind: MindState, panel: QuestionPanel) -> RawDecision:
        self.calls += 1
        chosen = self._choose(mind, panel)
        action = {
            affordance.key: (0.9 if affordance.key == chosen else 0.1 / max(1, len(panel.menu) - 1))
            for affordance in panel.menu
        }
        calls = {call.value: (1.0 if call == Call.SILENT else 0.0) for call in panel.calls}
        focus = {key: (1.0 if key == NOTHING_IN_PARTICULAR else 0.0) for key in panel.focus.criteria}
        return RawDecision(
            mind.organism_id,
            _choice(action),
            _score(1.0, EFFORT_LEVEL_COUNT),
            _score(0.0, THREAT_LEVEL_COUNT),
            _choice(calls),
            _choice(focus),
            "scripted",
            0,
            0.0,
            1,
        )

    async def close(self) -> None:
        return None
