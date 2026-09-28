from __future__ import annotations

import math

from lifeform.actions.calls import CALL_SPECS, Call
from lifeform.actions.verbs import Verb
from lifeform.core.events import EventKind
from lifeform.simulation.context import TickContext
from lifeform.world.acoustics import SoundEvent

VOCAL_BASE = 0.6
VOCAL_SPAN = 0.4
FOOTSTEP_BASE_DB = 35.0
FOOTSTEP_DB_PER_LOG_MASS = 8.0
FAST_EFFORT = 2
MARK_MUSK_MULTIPLIER = 5.0


class SignalEmitter:
    def emit_calls(self, context: TickContext) -> None:
        for organism in context.population.living():
            intent = context.intents.get(organism.id)
            if intent is None or intent.call == Call.SILENT:
                continue
            spec = CALL_SPECS[intent.call]
            level = spec.level_db * (VOCAL_BASE + VOCAL_SPAN * organism.trait("vocal_capacity"))
            context.world.sounds.emit(
                SoundEvent(organism.id, organism.species_id, organism.position, intent.call.value, level, True)
            )
            context.emit(EventKind.CALL, (organism.id,), organism.position, call=intent.call.value)

    def emit_marks(self, context: TickContext) -> None:
        scent = context.services.ecology.scent
        for organism in context.population.living():
            intent = context.intents.get(organism.id)
            if intent is None or intent.affordance.verb != Verb.SCENT_MARK:
                continue
            context.world.marks.place(organism.id, organism.species_id, organism.position)
            channel = context.world.fields.scent.musk_channel(organism.species_id)
            context.world.fields.scent.emit(
                channel,
                organism.position.x,
                organism.position.y,
                MARK_MUSK_MULTIPLIER * scent.musk_emission_per_kg075 * organism.body.mass_kg**0.75,
            )

    def emit_footsteps(self, context: TickContext, moved: dict[int, int]) -> None:
        for organism_id, effort in moved.items():
            organism = context.population.get(organism_id)
            if organism is None or effort < FAST_EFFORT:
                continue
            level = FOOTSTEP_BASE_DB + FOOTSTEP_DB_PER_LOG_MASS * math.log10(max(organism.body.mass_kg, 1.0))
            context.world.sounds.emit(
                SoundEvent(organism.id, organism.species_id, organism.position, "footsteps", level, False)
            )

    @staticmethod
    def emit_noise(context: TickContext, source_id: int, kind: str, level_db: float) -> None:
        organism = context.population.any(source_id)
        if organism is None:
            return
        context.world.sounds.emit(SoundEvent(source_id, organism.species_id, organism.position, kind, level_db, False))
