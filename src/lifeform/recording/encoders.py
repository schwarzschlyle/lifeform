from __future__ import annotations

from typing import Any

import numpy as np

from lifeform.actions.calls import CALL_CODE, Call
from lifeform.actions.verbs import STALLED_CODE, VERB_CODE, Verb
from lifeform.biology.drives import Condition
from lifeform.biology.organism import Organism
from lifeform.cognition.decision import Band, Intent, RawDecision
from lifeform.simulation.context import TickContext
from lifeform.simulation.services import Ecosystem
from lifeform.world.terrain import FoodLayer
from lifeform.world.world import World

BYTE = 255
GRAMS_PER_KG = 1000
BAND_CODE: dict[Band, int] = {Band.DECISIVE: 0, Band.HESITANT: 1, Band.DITHERING: 2}
OUTCOME_OK, OUTCOME_FAILED, OUTCOME_STALLED = 0, 1, 2
WATER_SCALE_M = 3.0
SNOW_SCALE_CM = 150.0
FIELD_SCALE_HEADROOM = 1.2
TRACKED_TRAITS: tuple[str, ...] = (
    "body_mass",
    "limb_ratio",
    "armor",
    "weaponry",
    "insulation",
    "fat_capacity",
    "crypsis",
    "ornament",
    "toxicity",
    "endothermy",
    "visual_acuity",
    "night_vision",
    "olfaction",
    "hearing",
    "offspring_investment",
    "boldness",
    "sociability",
    "aggression",
    "vigilance",
    "curiosity",
    "activity_phase",
    "decisiveness",
    "caution",
    "swim_skill",
    "climb_skill",
    "dig_skill",
    "water_efficiency",
    "toxin_resistance",
    "immune_investment",
)


def _byte(value: float) -> int:
    return int(max(0.0, min(1.0, value)) * BYTE)


class FrameEncoder:
    def __init__(self, services: Ecosystem) -> None:
        self._services = services

    def frame(self, world: World, organisms: list[Organism], context: TickContext | None) -> dict[str, Any]:
        columns: dict[str, list[int]] = {
            name: []
            for name in (
                "id",
                "species",
                "x",
                "y",
                "heading",
                "verb",
                "target",
                "effort",
                "band",
                "call",
                "confidence",
                "energy",
                "hydration",
                "health",
                "fear",
                "sleep",
                "mass",
                "flags",
                "outcome",
                "sex",
                "age",
            )
        }
        paths: dict[int, list[int]] = {}
        for organism in organisms:
            intent = context.intents.get(organism.id) if context else None
            record = context.records.get(organism.id) if context else None
            self._organism_columns(columns, organism, intent, context)
            columns["outcome"].append(self._outcome(intent, record.outcome if record else None))
            if record is not None and record.path:
                paths[organism.id] = [coordinate for step in record.path for coordinate in (step.x, step.y)]
        return {"tick": world.tick, "clock": self._clock(world), "organisms": columns, "paths": paths}

    def _organism_columns(
        self, columns: dict[str, list[int]], organism: Organism, intent: Intent | None, context: TickContext | None
    ) -> None:
        mechanics = self._services.mechanics
        body = organism.body
        conditions = context.conditions.get(organism.id, Condition.NONE) if context else Condition.NONE
        target = intent.affordance.target_id if intent and intent.affordance.target_id is not None else 0
        values: dict[str, int] = {
            "id": organism.id,
            "species": organism.species_id,
            "x": body.position.x,
            "y": body.position.y,
            "heading": int(body.heading),
            "verb": STALLED_CODE if intent is None or intent.stalled else VERB_CODE[intent.affordance.verb],
            "target": target,
            "effort": intent.effort if intent else 0,
            "band": BAND_CODE[intent.band] if intent else 0,
            "call": CALL_CODE[intent.call] if intent else CALL_CODE[Call.SILENT],
            "confidence": _byte(intent.confidence) if intent else 0,
            "energy": _byte(mechanics.energy_fraction(organism)),
            "hydration": _byte(body.hydration),
            "health": _byte(body.health),
            "fear": _byte(body.fear),
            "sleep": _byte(body.sleep_pressure),
            "mass": int(body.mass_kg * GRAMS_PER_KG),
            "flags": int(conditions | (Condition.ASLEEP if body.asleep else Condition.NONE)),
            "sex": 0 if organism.reproduction.is_female else 1,
            "age": body.age_ticks,
        }
        for name, value in values.items():
            columns[name].append(value)

    @staticmethod
    def _outcome(intent: Intent | None, outcome: str | None) -> int:
        if intent is None or intent.stalled:
            return OUTCOME_STALLED
        return OUTCOME_FAILED if outcome else OUTCOME_OK

    @staticmethod
    def _clock(world: World) -> dict[str, Any]:
        calendar = world.calendar
        state = world.climate_state
        return {
            "tick_of_day": calendar.tick_of_day(world.tick),
            "day": calendar.day_index(world.tick),
            "season": calendar.season_index(world.tick),
            "season_word": calendar.season_word(world.tick),
            "phase": calendar.day_phase_word(world.tick),
            "light": round(float(state.light.mean()), 3),
            "sun": round(float(np.percentile(state.light, 90)), 3),
            "weather": int(state.weather),
            "wind": [round(state.wind[0], 3), round(state.wind[1], 3)],
            "temperature": round(float(state.temperature.mean()), 2),
        }


class FieldEncoder:
    def __init__(self, world: World) -> None:
        capacity = world.fields.vegetation.capacity
        self.scales: dict[str, float] = {
            layer.key: max(float(capacity[layer].max()) * FIELD_SCALE_HEADROOM, 1e-6) for layer in FoodLayer
        }
        self.scales.update(
            {"water": WATER_SCALE_M, "snow": SNOW_SCALE_CM, "fire": 1.0, "canopy": 1.0, "toxin": 1.0, "pathogen": 1.0}
        )

    def keyframe(self, world: World) -> dict[str, Any]:
        fields = world.fields
        layers: dict[str, bytes] = {
            layer.key: self._quantize(fields.vegetation.biomass[layer], self.scales[layer.key]) for layer in FoodLayer
        }
        layers["water"] = self._quantize(fields.hydrology.surface_water, WATER_SCALE_M)
        layers["snow"] = self._quantize(fields.hydrology.snow_depth, SNOW_SCALE_CM)
        layers["fire"] = self._quantize(fields.fire.intensity, 1.0)
        layers["canopy"] = self._quantize(fields.canopy, 1.0)
        layers["toxin"] = self._quantize(fields.toxin.level, 1.0)
        layers["pathogen"] = self._quantize(fields.pathogen.total(), 1.0)
        return {"tick": world.tick, "layers": layers, "terrain_changed": False}

    @staticmethod
    def _quantize(grid: np.ndarray, scale: float) -> bytes:
        return (np.clip(grid / scale, 0.0, 1.0) * BYTE).astype(np.uint8).tobytes()


class DecisionEncoder:
    def __init__(self, detail: str) -> None:
        self._detail = detail

    def record(self, context: TickContext, organism_id: int) -> dict[str, Any] | None:
        decision = context.decisions.get(organism_id)
        intent = context.intents.get(organism_id)
        panel = context.panels.get(organism_id)
        mind = context.minds.get(organism_id)
        if decision is None or intent is None or panel is None or self._detail == "none":
            return None
        record = context.records.get(organism_id)
        entry: dict[str, Any] = {
            "id": organism_id,
            "menu": [[affordance.key, affordance.description] for affordance in panel.menu],
            "answers": self._answers(decision),
            "sampled": intent.sampled_key,
            "argmax": intent.argmax_key,
            "band": intent.band.value,
            "effort": intent.effort,
            "urgent": intent.urgent,
            "call": intent.call.value,
            "focus": intent.focus_label,
            "outcome": record.outcome if record else None,
            "model": decision.model,
            "tokens": decision.input_tokens,
            "latency_ms": round(decision.latency_ms, 1),
            "attempts": decision.attempts,
        }
        if self._detail == "full" and mind is not None:
            entry["state"] = mind.payload
        return entry

    @staticmethod
    def _answers(decision: RawDecision) -> dict[str, Any]:
        rounded = _rounded_distribution
        return {
            "action": {
                "choice": decision.action.choice,
                "confidence": round(decision.action.confidence, 4),
                "probabilities": rounded(decision.action.probabilities),
            },
            "effort": {
                "score": round(decision.effort.score, 3),
                "probabilities": rounded(decision.effort.probabilities),
            },
            "threat": {
                "score": round(decision.threat.score, 3),
                "probabilities": rounded(decision.threat.probabilities),
            },
            "call": {"choice": decision.call.choice, "probabilities": rounded(decision.call.probabilities)},
            "focus": {"choice": decision.focus.choice, "probabilities": rounded(decision.focus.probabilities)},
        }


def _rounded_distribution(probabilities: dict[Any, float]) -> dict[str, float]:
    return {str(key): round(value, 4) for key, value in probabilities.items()}


def organism_summary(organism: Organism, species_name: str) -> dict[str, Any]:
    phenotype = organism.phenotype
    return {
        "id": organism.id,
        "name": organism.identity.name,
        "species": organism.species_id,
        "species_name": species_name,
        "sex": organism.reproduction.sex.value,
        "birth_tick": organism.identity.birth_tick,
        "death_tick": organism.death_tick,
        "death_cause": organism.death_cause,
        "mother": organism.lineage.mother_id,
        "father": organism.lineage.father_id,
        "generation": organism.lineage.generation,
        "archetype": organism.identity.archetype,
        "adult_mass_kg": round(phenotype.adult_mass_kg, 3),
        "diet": [round(phenotype.diet.fiber, 3), round(phenotype.diet.soft, 3), round(phenotype.diet.animal, 3)],
        "traits": {name: round(phenotype.trait(name), 4) for name in TRACKED_TRAITS},
        "instincts": sorted(phenotype.instincts),
        "genotype": [round(float(value), 3) for value in organism.genome.genotype],
        "offspring": organism.reproduction.offspring_count,
    }


VERB_NAMES: list[str] = [verb.value for verb in Verb]
CALL_NAMES: list[str] = [call.value for call in Call]
CONDITION_NAMES: list[str] = [flag.name.lower() for flag in Condition if flag.name and flag != Condition.NONE]
