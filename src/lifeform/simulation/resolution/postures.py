from __future__ import annotations

from lifeform.actions.verbs import VERB_SPECS, Verb
from lifeform.cognition.decision import Band
from lifeform.simulation.context import TickContext
from lifeform.world.terrain import TerrainType

HIDING_COVER = 0.3
RESTING_VERBS = frozenset({Verb.REST, Verb.SLEEP, Verb.BASK, Verb.HUDDLE, Verb.GROOM_SELF, Verb.SUCKLE})
CALL_ACTIVITY = 0.2
CLIMBABLE = frozenset({TerrainType.FOREST, TerrainType.RAINFOREST})


class PostureResolver:
    def apply(self, context: TickContext) -> None:
        services = context.services
        world = context.world
        perception = services.ecology.perception
        dithering_bonus = services.ecology.cognition.dithering_certainty_bonus
        for organism in context.population.living():
            intent = context.intents.get(organism.id)
            record = context.record(organism.id)
            body = organism.body
            body.certainty_bonus = 0.0
            body.radius_bonus = 0.0
            if intent is None or intent.stalled:
                record.activity.pal = VERB_SPECS[Verb.REST].pal
                record.outcome = "stalled"
                continue
            verb = intent.affordance.verb
            spec = VERB_SPECS[verb]
            body.reset_postures()
            body.asleep = verb == Verb.SLEEP
            if spec.moves:
                body.climbing = False
                body.in_den = False
            self._set_posture(verb, context, organism.id)
            if intent.band == Band.DITHERING and not intent.urgent:
                body.certainty_bonus = dithering_bonus
            if verb == Verb.SCAN:
                body.radius_bonus = perception.scan_radius_bonus
                body.certainty_bonus = max(body.certainty_bonus, perception.scan_certainty_bonus)
            if body.in_den:
                body.hidden = True
            record.activity.pal = spec.pal + (CALL_ACTIVITY if intent.call.value != "silent" else 0.0)
            record.activity.effort = intent.effort
            record.activity.resting = verb in RESTING_VERBS
            record.activity.sleeping = verb == Verb.SLEEP
            body.last_actions.append(verb.value)
            heavy = organism.body.mass_kg > services.ecology.vegetation.trample_mass_threshold_kg
            if heavy and spec.moves:
                world.fields.vegetation.trample(organism.position.x, organism.position.y)

    @staticmethod
    def _set_posture(verb: Verb, context: TickContext, organism_id: int) -> None:
        organism = context.population.organisms[organism_id]
        body = organism.body
        world = context.world
        mechanics = context.services.mechanics
        cover = world.cover(organism.position)
        if verb == Verb.HIDE and (cover >= HIDING_COVER or body.in_den):
            body.hidden = True
        elif verb == Verb.FREEZE:
            body.frozen = True
        elif verb in (Verb.BRACE, Verb.DEFEND_YOUNG, Verb.FIGHT_BACK):
            body.braced = True
        elif verb == Verb.AMBUSH:
            body.ambushing = True
            body.hidden = cover >= HIDING_COVER
        elif verb == Verb.PLAY_DEAD:
            body.playing_dead = True
        elif verb == Verb.STALK:
            body.stalking = True
        elif verb == Verb.CLIMB and mechanics.can_climb(organism) and world.terrain_at(organism.position) in CLIMBABLE:
            body.climbing = True
        elif verb == Verb.DESCEND:
            body.climbing = False
        elif verb == Verb.ENTER_DEN and world.dens.at(organism.position) is not None:
            body.in_den = True
        elif verb == Verb.LEAVE_DEN:
            body.in_den = False
