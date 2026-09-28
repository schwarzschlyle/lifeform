from __future__ import annotations

import math

from lifeform.config.parameters import EcologyParameters
from lifeform.ecology.foraging import carcass_is_depleted
from lifeform.world.terrain import FoodLayer
from lifeform.world.world import World

REFERENCE_DECAY_TEMPERATURE_C = 20.0
Q10_SPAN_C = 10.0
DECAY_Q10 = 2.5
INVERTEBRATE_BOOST_PER_KG = 0.3
INFECTED_CARCASS_SHEDDING = 0.02
INFECTED_CARCASS_HALF_LIFE_TICKS = 24.0


class CarcassDecay:
    def __init__(self, ecology: EcologyParameters) -> None:
        self._ecology = ecology

    def update(self, world: World) -> None:
        meat = self._ecology.meat
        scent = self._ecology.scent
        for carcass in list(world.carcasses.items.values()):
            position = carcass.position
            temperature = world.temperature(position)
            rate = meat.decay_rate_per_tick_at_20c * DECAY_Q10 ** (
                (temperature - REFERENCE_DECAY_TEMPERATURE_C) / Q10_SPAN_C
            )
            decayed = carcass.mass_kg * (1.0 - math.exp(-max(rate, 0.0)))
            carcass.mass_kg -= decayed
            carcass.age_ticks += 1
            carcass.spoilage = 1.0 - math.exp(-meat.spoilage_rate_per_tick * carcass.age_ticks)
            world.fields.nutrients.deposit(position.x, position.y, meat.decay_nutrient_per_kg * decayed)
            world.fields.vegetation.biomass[FoodLayer.INVERTEBRATES, position.y, position.x] += (
                INVERTEBRATE_BOOST_PER_KG * decayed * world.productivity_scale
            )
            world.fields.scent.emit("carrion", position.x, position.y, scent.carrion_emission_per_kg_decayed * decayed)
            if carcass.strain_id is not None:
                world.fields.pathogen.shed(
                    carcass.strain_id,
                    position.x,
                    position.y,
                    INFECTED_CARCASS_SHEDDING,
                    INFECTED_CARCASS_HALF_LIFE_TICKS,
                )
            if carcass_is_depleted(carcass):
                world.carcasses.remove(carcass.carcass_id)
