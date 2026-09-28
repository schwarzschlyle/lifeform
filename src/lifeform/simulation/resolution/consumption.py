from __future__ import annotations

from collections import defaultdict

from lifeform.actions.verbs import Verb
from lifeform.biology.body import MEAT_KEY
from lifeform.biology.organism import Organism
from lifeform.cognition.affordances import FOOD_VERBS
from lifeform.core.geometry import Position
from lifeform.ecology.contests import ContestModel
from lifeform.ecology.foraging import carcass_is_depleted
from lifeform.simulation.context import TickContext
from lifeform.world.terrain import FoodLayer

LAYER_BY_VERB: dict[Verb, FoodLayer] = {verb: layer for layer, verb in FOOD_VERBS.items()}
MEAGER_MEAL_KG = 1e-4


class ConsumptionResolver:
    def resolve(self, context: TickContext) -> None:
        self._graze(context)
        self._scavenge(context)
        self._drink(context)

    def _graze(self, context: TickContext) -> None:
        tables: dict[tuple[Position, FoodLayer], list[Organism]] = defaultdict(list)
        for organism in context.population.living():
            intent = context.intents.get(organism.id)
            if intent is None or intent.stalled or intent.affordance.verb not in LAYER_BY_VERB:
                continue
            tables[(organism.position, LAYER_BY_VERB[intent.affordance.verb])].append(organism)
        forager = context.services.forager
        for (_, layer), eaters in tables.items():
            for organism, share in self._shares(eaters):
                eaten = forager.eat_layer(organism, context.world, layer, context.intents[organism.id].effort, share)
                record = context.record(organism.id)
                record.ate_kg += eaten
                if eaten < MEAGER_MEAL_KG:
                    record.outcome = "tried to eat, but found almost nothing"
                else:
                    organism.memory.spatial.remember(f"food:{layer.key}", organism.position, eaten, context.tick)

    def _scavenge(self, context: TickContext) -> None:
        tables: dict[int, list[Organism]] = defaultdict(list)
        for organism in context.population.living():
            intent = context.intents.get(organism.id)
            if intent is None or intent.stalled or intent.affordance.verb != Verb.EAT_CARCASS:
                continue
            carcass_id = intent.affordance.target_id
            carcass = context.world.carcasses.items.get(carcass_id or -1)
            if carcass is None or not context.world.metric.are_adjacent(organism.position, carcass.position):
                context.record(organism.id).outcome = "went to feed, but the carcass was gone"
                continue
            tables[carcass.carcass_id].append(organism)
        forager = context.services.forager
        for carcass_id, eaters in tables.items():
            carcass = context.world.carcasses.items[carcass_id]
            for organism, share in self._shares(eaters):
                eaten = forager.eat_carcass(organism, carcass, context.intents[organism.id].effort, share)
                record = context.record(organism.id)
                record.ate_kg += eaten
                record.ate_meat_of = carcass.species_id
                organism.memory.spatial.remember(MEAT_KEY, carcass.position, carcass.mass_kg, context.tick)
            if carcass_is_depleted(carcass):
                context.world.carcasses.remove(carcass_id)

    def _drink(self, context: TickContext) -> None:
        forager = context.services.forager
        for organism in context.population.living():
            intent = context.intents.get(organism.id)
            if intent is None or intent.stalled or intent.affordance.verb != Verb.DRINK:
                continue
            source = context.world.drinkable_near(organism.position)
            record = context.record(organism.id)
            if source is None:
                record.outcome = "went to drink, but the water was gone"
                continue
            litres = forager.drink(organism, context.world, source, intent.effort)
            record.drank_litres += litres
            record.activity.drank_litres += litres
            organism.memory.spatial.remember("water", source, 1.0, context.tick)

    @staticmethod
    def _shares(eaters: list[Organism]) -> list[tuple[Organism, float]]:
        weights = [ContestModel.priority(organism) for organism in eaters]
        total = sum(weights)
        ranked = sorted(zip(eaters, weights, strict=True), key=_weight, reverse=True)
        return [(organism, weight / total if total > 0 else 1.0 / len(eaters)) for organism, weight in ranked]


def _weight(entry: tuple[Organism, float]) -> float:
    return entry[1]
