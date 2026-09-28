from __future__ import annotations

import numpy as np

from lifeform.actions.calls import Call
from lifeform.actions.verbs import Verb
from lifeform.biology.organism import Organism
from lifeform.cognition.affordances import Affordance
from lifeform.cognition.decision import Band, Intent, RawDecision
from lifeform.cognition.question_panel import NOTHING_IN_PARTICULAR, QuestionPanel
from lifeform.config.parameters import CognitionParameters

MAX_EFFORT = 3
THREAT_LEVELS = 4.0
STALLED_AFFORDANCE = Affordance("stalled", Verb.REST, "did nothing")


def most_probable(probabilities: dict[str, float], keys: list[str]) -> str:
    best_key = keys[0]
    best = -1.0
    for key in keys:
        probability = probabilities.get(key, 0.0)
        if probability > best:
            best_key, best = key, probability
    return best_key


class DecisivenessSampler:
    def __init__(self, rng: np.random.Generator) -> None:
        self._rng = rng

    def sample(self, probabilities: dict[str, float], allowed: list[str], decisiveness: float) -> str:
        weights = np.array([max(probabilities.get(key, 0.0), 0.0) for key in allowed], dtype=np.float64)
        if weights.sum() <= 0.0:
            return allowed[0]
        sharpened = weights**decisiveness
        total = sharpened.sum()
        if total <= 0.0 or not np.isfinite(total):
            return allowed[int(np.argmax(weights))]
        return allowed[int(self._rng.choice(len(allowed), p=sharpened / total))]


class HesitationRule:
    def __init__(self, parameters: CognitionParameters) -> None:
        self._parameters = parameters

    def band(self, confidence: float, caution: float) -> Band:
        parameters = self._parameters
        low = parameters.hesitation_low_base + parameters.hesitation_caution_span * caution
        high = parameters.hesitation_high_base + parameters.hesitation_caution_span * caution
        if confidence >= high:
            return Band.DECISIVE
        if confidence >= low:
            return Band.HESITANT
        return Band.DITHERING

    @staticmethod
    def effort_after(effort: int, band: Band, urgent: bool) -> int:
        if urgent or band == Band.DECISIVE:
            return effort
        return max(0, effort - 1)


class DecisionInterpreter:
    def __init__(self, parameters: CognitionParameters, rng: np.random.Generator) -> None:
        self._parameters = parameters
        self._sampler = DecisivenessSampler(rng)
        self._hesitation = HesitationRule(parameters)

    def interpret(self, organism: Organism, panel: QuestionPanel, raw: RawDecision) -> Intent:
        keys = [affordance.key for affordance in panel.menu]
        beta = organism.phenotype.decisiveness
        sampled_key = self._sampler.sample(raw.action.probabilities, keys, beta)
        argmax_key = most_probable(raw.action.probabilities, keys)
        affordance = panel.affordance(sampled_key) or panel.menu[0]
        urgent = round(raw.threat.score) >= self._parameters.urgent_threat_level
        band = self._hesitation.band(raw.action.confidence, organism.trait("caution"))
        effort = min(MAX_EFFORT, max(0, round(raw.effort.score)))
        call_keys = [call.value for call in panel.calls]
        call = Call(self._sampler.sample(raw.call.probabilities, call_keys, beta)) if call_keys else Call.SILENT
        focus = raw.focus.choice if raw.focus.choice != NOTHING_IN_PARTICULAR else None
        return Intent(
            organism_id=organism.id,
            affordance=affordance,
            effort=self._hesitation.effort_after(effort, band, urgent),
            band=band,
            urgent=urgent,
            call=call,
            focus_label=focus,
            threat_score=raw.threat.score,
            sampled_key=sampled_key,
            argmax_key=argmax_key,
            confidence=raw.action.confidence,
        )

    def appraise_fear(self, organism: Organism, threat_score: float) -> None:
        rate = self._parameters.fear_integration_rate
        organism.body.fear = (1.0 - rate) * organism.body.fear + rate * min(1.0, threat_score / THREAT_LEVELS)

    @staticmethod
    def stalled(organism: Organism) -> Intent:
        return Intent(
            organism.id,
            STALLED_AFFORDANCE,
            0,
            Band.DITHERING,
            False,
            Call.SILENT,
            None,
            0.0,
            "stalled",
            "stalled",
            0.0,
            stalled=True,
        )
