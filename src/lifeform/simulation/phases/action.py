from __future__ import annotations

from lifeform.actions.verbs import Verb
from lifeform.biology.organism import Organism
from lifeform.simulation.context import TickContext
from lifeform.simulation.resolution.consumption import ConsumptionResolver
from lifeform.simulation.resolution.interactions import InteractionResolver
from lifeform.simulation.resolution.movement import SubStepMover
from lifeform.simulation.resolution.planning import MovementPlanner
from lifeform.simulation.resolution.postures import PostureResolver
from lifeform.simulation.resolution.signals import SignalEmitter
from lifeform.world.terrain import TerrainType

AMBUSH_PREY_MASS_RATIO = 1.5
FAST_EFFORT = 2
BASKING_LIGHT = 0.5
SHADE_CANOPY = 0.4
PURSUIT_VERBS = frozenset({Verb.CHASE, Verb.ATTACK, Verb.STALK})
WATER_TERRAIN = frozenset({TerrainType.SHALLOW_WATER, TerrainType.DEEP_WATER})


def ambush_suitable(ambusher: Organism, prey: Organism) -> bool:
    smaller = prey.body.mass_kg < AMBUSH_PREY_MASS_RATIO * ambusher.body.mass_kg
    return prey.species_id != ambusher.species_id and smaller and prey.alive


class ActionPhase:
    name = "action"

    def __init__(self) -> None:
        self._signals = SignalEmitter()
        self._postures = PostureResolver()
        self._planner = MovementPlanner()
        self._interactions = InteractionResolver(self._signals)
        self._consumption = ConsumptionResolver()

    def run(self, context: TickContext) -> None:
        self._signals.emit_calls(context)
        self._postures.apply(context)
        plans = self._planner.plans(context)
        ambushers = [organism for organism in context.population.living() if organism.body.ambushing]
        mover = SubStepMover(context.world, context.population, context.services.streams.stream("initiative"))
        report = mover.run(plans, ambushers, ambush_suitable)
        context.population.reindex()
        moved_efforts: dict[int, int] = {}
        for plan in plans:
            record = context.record(plan.organism.id)
            record.path = report.paths.get(plan.organism.id, [])
            record.activity.locomotion_units = report.locomotion_units.get(plan.organism.id, 0.0)
            if record.path:
                moved_efforts[plan.organism.id] = plan.effort
        context.persistent.moved_fast = {
            organism_id for organism_id, effort in moved_efforts.items() if effort >= FAST_EFFORT
        }
        self._signals.emit_footsteps(context, moved_efforts)
        self._mark_pursuits(context)
        self._interactions.resolve(context, report)
        self._consumption.resolve(context)
        self._signals.emit_marks(context)
        self._microclimates(context)

    @staticmethod
    def _mark_pursuits(context: TickContext) -> None:
        for organism in context.population.living():
            organism.body.chased_by = None
        for organism in context.population.living():
            intent = context.intents.get(organism.id)
            if intent is None or intent.affordance.verb not in PURSUIT_VERBS:
                continue
            target = context.population.get(intent.affordance.target_id)
            if target is not None:
                target.body.chased_by = organism.id

    @staticmethod
    def _microclimates(context: TickContext) -> None:
        world = context.world
        for organism in context.population.living():
            intent = context.intents.get(organism.id)
            verb = intent.affordance.verb if intent is not None else None
            record = context.record(organism.id)
            position = organism.position
            resting = record.activity.resting or record.activity.sleeping
            record.basking = verb == Verb.BASK and world.light(position) > BASKING_LIGHT
            record.shaded = verb == Verb.SEEK_SHADE or (resting and world.canopy(position) >= SHADE_CANOPY)
            record.in_water = verb == Verb.WALLOW or world.terrain_at(position) in WATER_TERRAIN
            record.huddling = verb == Verb.HUDDLE and any(
                other.species_id == organism.species_id and other.id != organism.id
                for other in context.population.within(position, 1.5)
            )
