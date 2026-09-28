from __future__ import annotations

from lifeform.actions.verbs import VERB_SPECS, Verb
from lifeform.biology.organism import Organism
from lifeform.cognition.affordances import TargetKind
from lifeform.cognition.decision import Band, Intent
from lifeform.core.geometry import Position
from lifeform.simulation.context import TickContext
from lifeform.simulation.resolution.movement import MoveMode, MoverPlan

ADJACENT_STOP = 1.0
INVESTIGATE_STOP = 2.0
INVESTIGATE_MAX_STEPS = 2
STALK_STEPS = 1
DITHERING_STEPS = 1

TOWARD_VERBS = frozenset(
    {
        Verb.APPROACH,
        Verb.FOLLOW,
        Verb.CHASE,
        Verb.ATTACK,
        Verb.MOB,
        Verb.CHALLENGE,
        Verb.COURT,
        Verb.STEAL_FOOD,
        Verb.STALK,
        Verb.INVESTIGATE,
    }
)
DESTINATION_VERBS = frozenset({Verb.GO_TO_MEMORY, Verb.SEEK_SHADE, Verb.STAY_WITH_GROUP, Verb.DEFEND_YOUNG})


class MovementPlanner:
    def plans(self, context: TickContext) -> list[MoverPlan]:
        plans: list[MoverPlan] = []
        for organism in context.population.living():
            intent = context.intents.get(organism.id)
            if intent is None or intent.stalled or not VERB_SPECS[intent.affordance.verb].moves:
                continue
            steps = self._steps(context, organism, intent)
            plan = self._plan(context, organism, intent, steps)
            if plan is not None and plan.steps > 0:
                plans.append(plan)
        return plans

    def _steps(self, context: TickContext, organism: Organism, intent: Intent) -> int:
        steps = context.services.mechanics.steps_for_effort(organism, intent.effort, context.tick)
        verb = intent.affordance.verb
        if verb == Verb.STALK:
            steps = min(steps, STALK_STEPS)
        if verb == Verb.INVESTIGATE:
            steps = min(steps, INVESTIGATE_MAX_STEPS)
        if intent.band == Band.DITHERING and not intent.urgent:
            steps = min(steps, DITHERING_STEPS)
        return steps

    def _plan(self, context: TickContext, organism: Organism, intent: Intent, steps: int) -> MoverPlan | None:
        affordance = intent.affordance
        verb = affordance.verb
        if verb == Verb.MOVE or (
            verb in (Verb.FLEE, Verb.FOLLOW_SCENT) and affordance.target_kind in (TargetKind.SCENT, TargetKind.SOUND)
        ):
            return MoverPlan(organism, steps, MoveMode.DIRECTION, intent.effort, direction=affordance.direction)
        if verb == Verb.FLEE:
            return MoverPlan(
                organism,
                steps,
                MoveMode.AWAY,
                intent.effort,
                target_id=affordance.target_id,
                point=self._target_point(context, affordance.target_kind, affordance.target_id),
            )
        if verb in TOWARD_VERBS:
            return self._toward(context, organism, intent, steps)
        if verb in DESTINATION_VERBS:
            point = self._destination(context, organism, intent)
            return MoverPlan(
                organism,
                steps,
                MoveMode.DESTINATION,
                intent.effort,
                point=point,
                stop_distance=ADJACENT_STOP if verb in (Verb.STAY_WITH_GROUP, Verb.DEFEND_YOUNG) else 0.0,
            )
        return None

    def _toward(self, context: TickContext, organism: Organism, intent: Intent, steps: int) -> MoverPlan:
        affordance = intent.affordance
        stop = INVESTIGATE_STOP if affordance.verb == Verb.INVESTIGATE else ADJACENT_STOP
        if affordance.target_kind == TargetKind.SOUND:
            return MoverPlan(
                organism, steps, MoveMode.DESTINATION, intent.effort, point=affordance.destination, stop_distance=stop
            )
        point = self._target_point(context, affordance.target_kind, affordance.target_id)
        mode = MoveMode.TOWARD if affordance.target_kind == TargetKind.ANIMAL else MoveMode.DESTINATION
        return MoverPlan(
            organism, steps, mode, intent.effort, target_id=affordance.target_id, point=point, stop_distance=stop
        )

    def _destination(self, context: TickContext, organism: Organism, intent: Intent) -> Position | None:
        verb = intent.affordance.verb
        if verb == Verb.STAY_WITH_GROUP:
            return self._group_center(context, organism)
        if verb == Verb.DEFEND_YOUNG:
            young = [context.population.get(young_id) for young_id in organism.reproduction.dependents]
            living = [child for child in young if child is not None and child.alive]
            return living[0].position if living else None
        return intent.affordance.destination

    @staticmethod
    def _target_point(context: TickContext, kind: TargetKind, target_id: int | None) -> Position | None:
        if target_id is None:
            return None
        if kind == TargetKind.CARCASS:
            carcass = context.world.carcasses.items.get(target_id)
            return carcass.position if carcass is not None else None
        target = context.population.get(target_id)
        return target.position if target is not None else None

    @staticmethod
    def _group_center(context: TickContext, organism: Organism) -> Position | None:
        radius = context.services.ecology.social.group_radius_patches * 3
        kin = [
            other
            for other in context.population.within(organism.position, radius)
            if other.species_id == organism.species_id and other.id != organism.id
        ]
        if not kin:
            return None
        metric = context.world.metric
        offsets = [metric.delta(organism.position, other.position) for other in kin]
        mean_x = sum(offset[0] for offset in offsets) / len(offsets)
        mean_y = sum(offset[1] for offset in offsets) / len(offsets)
        return metric.wrap(organism.position.x + round(mean_x), organism.position.y + round(mean_y))
