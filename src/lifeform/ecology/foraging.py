from __future__ import annotations

import numpy as np

from lifeform.biology import allometry
from lifeform.biology.body import MEAT_KEY
from lifeform.biology.mechanics import EFFORT_FORCE, BodyMechanics
from lifeform.biology.organism import Organism
from lifeform.config.parameters import EcologyParameters
from lifeform.core.geometry import Position
from lifeform.world.entities import Carcass
from lifeform.world.terrain import FoodLayer
from lifeform.world.world import World

TOXIC_CARCASS_DOSE = 0.5
MIN_CARCASS_KG = 0.05
SKILL_BASE = 0.5
CANOPY_FRUIT_BONUS = 1.3


class Forager:
    def __init__(self, ecology: EcologyParameters, mechanics: BodyMechanics, rng: np.random.Generator) -> None:
        self._ecology = ecology
        self._mechanics = mechanics
        self._rng = rng

    def bite(self, organism: Organism, handling_factor: float, effort: int, skill: float = 1.0) -> float:
        capacity = self._mechanics.bite_capacity(organism) * handling_factor * EFFORT_FORCE[effort] * skill
        return capacity * self._mechanics.performance(organism)

    def stomach_room(self, organism: Organism) -> float:
        return max(0.0, self._mechanics.stomach_capacity(organism) - organism.body.stomach_total())

    def layer_skill(self, organism: Organism, layer: FoodLayer) -> float:
        if layer == FoodLayer.INVERTEBRATES:
            return SKILL_BASE + organism.trait("dig_skill")
        if layer == FoodLayer.SEEDS:
            return SKILL_BASE + SKILL_BASE * organism.trait("dig_skill")
        if layer == FoodLayer.ALGAE:
            return SKILL_BASE + SKILL_BASE * organism.trait("swim_skill")
        if layer == FoodLayer.FRUIT and organism.body.climbing:
            return CANOPY_FRUIT_BONUS
        return 1.0

    def eat_layer(self, organism: Organism, world: World, layer: FoodLayer, effort: int, share: float) -> float:
        position = organism.position
        parameters = self._ecology.food_layers[layer.key]
        wanted = min(
            self.bite(organism, parameters.handling_factor, effort, self.layer_skill(organism, layer)),
            self.stomach_room(organism),
        )
        taken = self._from_caches(world, position, layer.key, wanted)
        snow = float(world.fields.hydrology.snow_depth[position.y, position.x])
        available = world.fields.vegetation.accessible(layer, position.x, position.y, snow) * share
        taken += world.fields.vegetation.consume(layer, position.x, position.y, min(wanted - taken, available))
        if taken > 0.0:
            organism.body.add_to_stomach(layer.key, taken)
        return taken

    def eat_carcass(self, organism: Organism, carcass: Carcass, effort: int, share: float) -> float:
        meat = self._ecology.meat
        wanted = min(
            self.bite(organism, meat.handling_factor, effort, SKILL_BASE + organism.trait("weaponry")),
            self.stomach_room(organism),
            carcass.mass_kg * share,
        )
        if wanted <= 0.0:
            return 0.0
        carcass.mass_kg -= wanted
        spoiled_fraction = meat.spoilage_assimilation_penalty * carcass.spoilage
        organism.body.add_to_stomach(MEAT_KEY, wanted * (1.0 - spoiled_fraction))
        poisoning = meat.spoilage_poisoning * carcass.spoilage * (1.0 - organism.trait("carrion_tolerance"))
        if self._rng.random() < poisoning:
            organism.body.toxin_load += carcass.spoilage * TOXIC_CARCASS_DOSE
        organism.body.toxin_load += carcass.toxicity * TOXIC_CARCASS_DOSE * wanted / max(organism.body.mass_kg, 1e-6)
        return wanted

    def drink(self, organism: Organism, world: World, source: Position, effort: int) -> float:
        water = self._ecology.water
        deficit = (1.0 - organism.body.hydration) * self._mechanics.body_water_litres(organism)
        intake = min(
            deficit,
            allometry.water_turnover(organism.body.mass_kg, water.drink_litres_per_tick_per_kg08)
            * EFFORT_FORCE[effort],
        )
        world.fields.hydrology.drink(source.x, source.y, intake)
        return intake

    @staticmethod
    def _from_caches(world: World, position: Position, layer_key: str, wanted: float) -> float:
        taken = 0.0
        for cache in world.caches.at(position):
            if cache.layer_key != layer_key or taken >= wanted:
                continue
            portion = min(cache.mass_kg, wanted - taken)
            cache.mass_kg -= portion
            taken += portion
        return taken


def carcass_is_depleted(carcass: Carcass) -> bool:
    return carcass.mass_kg < MIN_CARCASS_KG
