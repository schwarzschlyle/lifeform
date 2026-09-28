from __future__ import annotations

from lifeform.biology.drives import SocialSurroundings
from lifeform.biology.organism import Organism
from lifeform.perception.percepts import EntityKind, PerceptualField
from lifeform.simulation.context import TickContext
from lifeform.world.terrain import TerrainType

TOUCH_RADIUS = 1.5
NOVELTY_WORTH_NOTICING = 0.5
WAKING_DANGER = 0.3
PASTURE_SCAN_INTERVAL_TICKS = 3


class PerceptionPhase:
    name = "perception"

    def run(self, context: TickContext) -> None:
        world = context.world
        services = context.services
        calendar = world.calendar
        hour = calendar.hour_of_day(context.tick)
        season = calendar.season_index(context.tick)
        moved_fast = context.persistent.moved_fast.__contains__
        group_radius = services.ecology.social.group_radius_patches
        for organism in context.population.living():
            light = world.light(organism.position)
            radius = max(
                services.mechanics.vision_radius(organism, light),
                TOUCH_RADIUS,
                services.ecology.perception.base_vision_radius,
            )
            nearby = context.population.within(organism.position, radius)
            entities = services.vision.perceive_animals(organism, world, nearby, moved_fast)
            entities += services.vision.perceive_carcasses(
                organism, world, world.carcasses.near(organism.position, radius)
            )
            kind_nearby = any(other.species_id == organism.species_id and other.id != organism.id for other in nearby)
            field = PerceptualField(
                entities,
                services.olfaction.perceive(organism, world, kind_nearby),
                services.hearing.perceive(organism, world),
            )
            surroundings = self._surroundings(organism, nearby, field, context, group_radius)
            drives = services.drives.compute(organism, hour, calendar.hours_per_day, context.tick, season, surroundings)
            swimming = world.terrain_at(organism.position) == TerrainType.DEEP_WATER
            context.conditions[organism.id] = services.conditions.read(organism, context.tick, season, swimming)
            services.salience.rank(organism, field, drives, context.population.any, world.carcasses.items.get)
            self._wake_if_disturbed(organism, field)
            self._note_surroundings(context, organism, field)
            if (context.tick + organism.id) % PASTURE_SCAN_INTERVAL_TICKS == 0:
                self._note_pasture(context, organism, radius)
            context.fields[organism.id] = field
            context.drives[organism.id] = drives

    @staticmethod
    def _surroundings(
        organism: Organism, nearby: list[Organism], field: PerceptualField, context: TickContext, group_radius: float
    ) -> SocialSurroundings:
        metric = context.world.metric
        kind_nearby = sum(
            1
            for other in nearby
            if other.species_id == organism.species_id
            and other.id != organism.id
            and metric.distance(organism.position, other.position) <= group_radius
        )
        seen = field.animal_ids()
        young_out_of_sight = any(young not in seen for young in organism.reproduction.dependents)
        return SocialSurroundings(kind_nearby, young_out_of_sight)

    @staticmethod
    def _wake_if_disturbed(organism: Organism, field: PerceptualField) -> None:
        if not organism.body.asleep:
            return
        touched_by_danger = any(percept.touching and percept.danger > WAKING_DANGER for percept in field.entities)
        if field.sounds or touched_by_danger:
            organism.body.asleep = False

    @staticmethod
    def _note_pasture(context: TickContext, organism: Organism, radius: float) -> None:
        view = context.services.forage_view
        here = view.assess(organism, context.world, organism.position)
        best = view.best_visible(organism, context.world, radius)
        if best is not None and view.worth_remembering(best, here):
            organism.memory.spatial.remember(f"food:{best.layer.key}", best.position, best.value, context.tick)

    @staticmethod
    def _note_surroundings(context: TickContext, organism: Organism, field: PerceptualField) -> None:
        memory = organism.memory
        novel = False
        for percept in field.entities:
            if percept.kind != EntityKind.ANIMAL:
                continue
            target = context.population.get(percept.target_id)
            if target is None or target.species_id == organism.species_id:
                continue
            key = f"species:{target.species_id}"
            novel = novel or memory.associations.novelty(key) > NOVELTY_WORTH_NOTICING
            memory.associations.expose(key)
        organism.body.ticks_since_novelty = 0 if novel else organism.body.ticks_since_novelty + 1
        water = context.world.drinkable_near(organism.position)
        if water is not None:
            memory.spatial.remember("water", water, 1.0, context.tick)
        den = context.world.dens.owned_by(organism.id)
        if den is not None:
            memory.spatial.remember("den", den.position, 1.0, context.tick)
