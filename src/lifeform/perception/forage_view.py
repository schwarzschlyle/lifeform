from __future__ import annotations

from dataclasses import dataclass

from lifeform.biology.mechanics import BodyMechanics
from lifeform.biology.organism import Organism
from lifeform.core.geometry import Position
from lifeform.world.terrain import FoodLayer
from lifeform.world.world import World

MIN_DIET_WEIGHT = 0.08
SCAN_STEP = 2
MAX_SCAN_RADIUS = 6
WORTH_REMEMBERING = 1.5


@dataclass(frozen=True, slots=True)
class FoodPatch:
    position: Position
    value: float
    layer: FoodLayer


class ForageView:
    """Judges how much edible food a patch holds for a given animal, in units of its own bites."""

    def __init__(self, mechanics: BodyMechanics) -> None:
        self._mechanics = mechanics

    def assess(self, organism: Organism, world: World, position: Position) -> FoodPatch:
        snow = float(world.fields.hydrology.snow_depth[position.y, position.x])
        bite = max(self._mechanics.bite_capacity(organism), 1e-6)
        best_layer = FoodLayer.GRASS
        best = 0.0
        total = 0.0
        for layer in FoodLayer:
            weight = organism.phenotype.diet.weight(world.ecology.food_layers[layer.key].diet_class)
            if weight < MIN_DIET_WEIGHT:
                continue
            value = weight * world.fields.vegetation.accessible(layer, position.x, position.y, snow) / bite
            total += value
            if value > best:
                best, best_layer = value, layer
        return FoodPatch(position, total, best_layer)

    def best_visible(self, organism: Organism, world: World, radius: float) -> FoodPatch | None:
        reach = int(min(radius, MAX_SCAN_RADIUS))
        best: FoodPatch | None = None
        origin = organism.position
        for dy in range(-reach, reach + 1, SCAN_STEP):
            for dx in range(-reach, reach + 1, SCAN_STEP):
                position = world.metric.wrap(origin.x + dx, origin.y + dy)
                if not world.is_passable(position, organism.trait("swim_skill")):
                    continue
                patch = self.assess(organism, world, position)
                if best is None or patch.value > best.value:
                    best = patch
        return best

    @staticmethod
    def worth_remembering(patch: FoodPatch | None, here: FoodPatch) -> bool:
        return patch is not None and patch.value >= WORTH_REMEMBERING and patch.value > here.value
