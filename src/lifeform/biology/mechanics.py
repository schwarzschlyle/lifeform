from __future__ import annotations

import math

from lifeform.biology import allometry
from lifeform.biology.organism import Organism
from lifeform.config.parameters import EcologyParameters

EFFORT_STEP_FRACTIONS: tuple[float, ...] = (0.0, 0.5, 0.75, 1.0)
EFFORT_FORCE: tuple[float, ...] = (0.8, 1.0, 1.1, 1.25)
EFFORT_ENERGY: tuple[float, ...] = (0.9, 1.0, 1.25, 1.7)
LATE_PREGNANCY_FRACTION = 2.0 / 3.0
LATE_PREGNANCY_SPEED = 0.9
EXHAUSTED_PERFORMANCE = 0.7
DEHYDRATED_BASE = 0.5
ECTOTHERM_COLD_LIMIT_BREADTHS = 1.5
ECTOTHERM_HEAT_LIMIT_BREADTHS = 0.6
ENDOTHERM_COLD_MARGIN_C = 6.0
ENDOTHERM_HEAT_MARGIN_C = 5.0
ATTACK_BASE = 0.3
ATTACK_WEAPON_SPAN = 2.2
DEFENSE_BASE = 0.5
MIN_HEARING_DB = 10.0
MAX_ECTOTHERM_RATE_FACTOR = 3.0
LIMB_SPEED_BASE = 0.7
LIMB_SPEED_SPAN = 0.7
ARMOR_SPEED_PENALTY = 0.25
FAT_SPEED_PENALTY = 0.1
JUVENILE_SPEED_EXPONENT = 0.25
MIN_PERFORMANCE = 0.05
SENESCENCE_DECLINE = 0.5
MIN_SENESCENCE_FACTOR = 0.3
ALTRICIAL_IMMOBILE_FRACTION = 0.5
CLIMB_SKILL_REQUIRED = 0.3
DEEP_SWIM_SKILL_REQUIRED = 0.5
DIG_SKILL_REQUIRED = 0.3
Q10_SPAN_C = 10.0


class BodyMechanics:
    def __init__(self, ecology: EcologyParameters) -> None:
        self._ecology = ecology

    def basal_rate(self, organism: Organism) -> float:
        metabolism = self._ecology.metabolism
        base = allometry.kleiber(organism.body.mass_kg, metabolism.basal_eu_per_tick_per_kg075)
        return base * organism.phenotype.basal_multiplier * self.ectotherm_rate_factor(organism)

    def ectotherm_rate_factor(self, organism: Organism) -> float:
        thermal = self._ecology.thermal
        endothermy = organism.phenotype.endothermy
        ectotherm = math.pow(
            thermal.q10, (organism.body.body_temperature_c - thermal.reference_temperature_c) / Q10_SPAN_C
        )
        return endothermy + (1.0 - endothermy) * min(ectotherm, MAX_ECTOTHERM_RATE_FACTOR)

    def energy_capacity(self, organism: Organism) -> float:
        fat_fraction = organism.trait("fat_capacity")
        return fat_fraction * organism.body.mass_kg * self._ecology.metabolism.fat_energy_density_eu_per_kg

    def energy_fraction(self, organism: Organism) -> float:
        return organism.body.energy_eu / max(self.energy_capacity(organism), 1e-9)

    def stomach_capacity(self, organism: Organism) -> float:
        return self._ecology.digestion.stomach_capacity_fraction_of_mass * organism.body.mass_kg

    def bite_capacity(self, organism: Organism) -> float:
        return allometry.kleiber(organism.body.mass_kg, self._ecology.digestion.bite_kg_per_tick_per_kg075)

    def body_water_litres(self, organism: Organism) -> float:
        return self._ecology.water.body_water_fraction * organism.body.mass_kg

    def top_speed(self, organism: Organism, tick: int) -> int:
        locomotion = self._ecology.locomotion
        phenotype = organism.phenotype
        fat_fill = min(1.0, self.energy_fraction(organism))
        speed = (
            locomotion.speed_coefficient
            * allometry.speed_scale(phenotype.adult_mass_kg)
            * (LIMB_SPEED_BASE + LIMB_SPEED_SPAN * organism.trait("limb_ratio"))
            * (1.0 - ARMOR_SPEED_PENALTY * organism.trait("armor"))
            * (1.0 - FAT_SPEED_PENALTY * fat_fill)
            * self.performance(organism)
        )
        if organism.body.limping:
            speed *= self._ecology.health.limp_speed_factor
        pregnancy = organism.reproduction.pregnancy
        if pregnancy is not None and pregnancy.progress(tick) > LATE_PREGNANCY_FRACTION:
            speed *= LATE_PREGNANCY_SPEED
        if self.is_immobile_newborn(organism):
            return 0
        speed *= min(1.0, organism.body.mass_kg / phenotype.adult_mass_kg) ** JUVENILE_SPEED_EXPONENT
        return int(min(locomotion.max_patches_per_tick, max(1, round(speed))))

    def steps_for_effort(self, organism: Organism, effort: int, tick: int) -> int:
        top = self.top_speed(organism, tick)
        if top == 0:
            return 0
        if organism.body.stamina <= 0.0:
            effort = min(effort, 1)
        if effort == 0:
            return 1
        return max(1, math.ceil(EFFORT_STEP_FRACTIONS[effort] * top))

    def is_immobile_newborn(self, organism: Organism) -> bool:
        if organism.reproduction.weaned:
            return False
        immobile_ticks = (
            ALTRICIAL_IMMOBILE_FRACTION * organism.phenotype.weaning_ticks * (1.0 - organism.trait("precociality"))
        )
        return organism.body.age_ticks < immobile_ticks

    def performance(self, organism: Organism) -> float:
        endothermy = organism.phenotype.endothermy
        ectotherm = self.thermal_performance(organism)
        performance = endothermy + (1.0 - endothermy) * ectotherm
        hydration = organism.body.hydration
        water = self._ecology.water
        if hydration < water.impaired_hydration:
            performance *= DEHYDRATED_BASE + hydration / (2.0 * water.impaired_hydration)
        if organism.body.stamina <= 0.0:
            performance *= EXHAUSTED_PERFORMANCE
        return max(MIN_PERFORMANCE, performance * self.senescence_factor(organism))

    def thermal_performance(self, organism: Organism) -> float:
        optimum = organism.trait("thermal_optimum")
        breadth = organism.trait("thermal_breadth")
        temperature = organism.body.body_temperature_c
        if temperature <= optimum:
            return math.exp(-(((temperature - optimum) / breadth) ** 2))
        ceiling = optimum + ECTOTHERM_HEAT_LIMIT_BREADTHS * breadth
        return max(0.0, 1.0 - ((temperature - optimum) / max(ceiling - optimum, 1e-6)) ** 2)

    def thermal_limits(self, organism: Organism) -> tuple[float, float]:
        endothermy = organism.phenotype.endothermy
        set_point = self._ecology.thermal.endotherm_set_point_c
        optimum = organism.trait("thermal_optimum")
        breadth = organism.trait("thermal_breadth")
        cold = endothermy * (set_point - ENDOTHERM_COLD_MARGIN_C) + (1.0 - endothermy) * (
            optimum - ECTOTHERM_COLD_LIMIT_BREADTHS * breadth
        )
        heat = endothermy * (set_point + ENDOTHERM_HEAT_MARGIN_C) + (1.0 - endothermy) * (
            optimum + ECTOTHERM_HEAT_LIMIT_BREADTHS * breadth
        )
        return cold, heat

    def senescence_factor(self, organism: Organism) -> float:
        lifespan = organism.phenotype.lifespan_ticks
        onset = self._ecology.aging.senescence_onset_fraction * lifespan
        age = organism.body.age_ticks
        if age <= onset:
            return 1.0
        return max(MIN_SENESCENCE_FACTOR, 1.0 - SENESCENCE_DECLINE * (age - onset) / lifespan)

    def is_senescent(self, organism: Organism) -> bool:
        onset = self._ecology.aging.senescence_onset_fraction * organism.phenotype.lifespan_ticks
        return organism.body.age_ticks > onset

    def attack_power(self, organism: Organism, effort: int) -> float:
        combat = self._ecology.combat
        weapon = ATTACK_BASE + ATTACK_WEAPON_SPAN * organism.trait("weaponry")
        return (
            combat.attack_coefficient
            * allometry.muscle_scale(organism.body.mass_kg)
            * weapon
            * self.performance(organism)
            * EFFORT_FORCE[effort]
        )

    def defense(self, organism: Organism) -> float:
        combat = self._ecology.combat
        guard = DEFENSE_BASE + organism.trait("armor") + combat.agility_defense_weight * organism.trait("limb_ratio")
        return combat.defense_coefficient * allometry.muscle_scale(organism.body.mass_kg) * guard

    def wound_capacity(self, organism: Organism) -> float:
        return self._ecology.combat.wound_capacity_coefficient * allometry.muscle_scale(organism.body.mass_kg)

    def vision_radius(self, organism: Organism, light: float) -> float:
        perception = self._ecology.perception
        base = perception.base_vision_radius + perception.acuity_vision_radius * organism.trait("visual_acuity")
        effective_light = light + perception.night_vision_compensation * organism.trait("night_vision") * (1 - light)
        radius = base * math.sqrt(max(effective_light, 0.0)) * (1.0 + organism.body.radius_bonus)
        return 0.0 if organism.body.asleep else radius

    def hearing_threshold_db(self, organism: Organism) -> float:
        perception = self._ecology.perception
        threshold = perception.base_hearing_threshold_db - perception.acuity_hearing_threshold_db * organism.trait(
            "hearing"
        )
        asleep_penalty = perception.wake_threshold_db if organism.body.asleep else 0.0
        return max(MIN_HEARING_DB, threshold + asleep_penalty)

    def smell_threshold(self, organism: Organism) -> float:
        perception = self._ecology.perception
        return perception.base_smell_threshold * math.pow(
            10.0, -perception.olfaction_smell_range * organism.trait("olfaction")
        )

    def can_climb(self, organism: Organism) -> bool:
        within_mass = organism.body.mass_kg <= self._ecology.locomotion.climb_mass_limit_kg
        return organism.trait("climb_skill") >= CLIMB_SKILL_REQUIRED and within_mass

    def can_swim_deep(self, organism: Organism) -> bool:
        return organism.trait("swim_skill") >= DEEP_SWIM_SKILL_REQUIRED and organism.body.stamina > 0.0

    def can_dig(self, organism: Organism) -> bool:
        return organism.trait("dig_skill") >= DIG_SKILL_REQUIRED

    def locomotion_cost_per_patch(self, organism: Organism) -> float:
        return allometry.locomotion_cost(
            organism.body.mass_kg, self._ecology.metabolism.locomotion_eu_per_patch_per_kg068
        )
