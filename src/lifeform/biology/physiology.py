from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np

from lifeform.biology import allometry
from lifeform.biology.body import MEAT_KEY
from lifeform.biology.mechanics import EFFORT_ENERGY, BodyMechanics
from lifeform.biology.organism import Organism
from lifeform.config.parameters import EcologyParameters

HUDDLE_CONDUCTANCE_FACTOR = 0.7
PAIN_REFERENCE_TICKS = 1.0
DAMAGE_LEDGER_RETENTION = 0.5
STRESS_SMOOTHING = 0.05
LITRES_PER_KG_FOOD_WATER = 1.0
STARVATION_MASS_FLOOR_FRACTION = 0.5
GRAZER_SPECIALIZATION = 0.5
WATER_EFFICIENCY_DIGESTION_COST = 0.05
CARRION_TOLERANCE_FRESH_MEAT_COST = 0.05
LACTATION_WATER_MULTIPLIER = 1.3
EVAPORATIVE_FAILURE_HYDRATION = 0.2
RESTING_CLOTTING_MULTIPLIER = 2.0
FED_ENERGY_FRACTION = 0.2
UNFED_HEALING_FRACTION = 0.2
STRESS_HEALING_PENALTY = 0.5
TOXIN_UPTAKE_PER_LEVEL = 0.1
MAX_TOXIN_LOAD = 1.5
ALL_OUT_EFFORT = 3
HURRIED_EFFORT = 2
THERMAL_STRAIN_SCALE_C = 10.0


@dataclass(slots=True)
class ActivityRecord:
    pal: float = 1.1
    effort: int = 1
    locomotion_units: float = 0.0
    resting: bool = False
    sleeping: bool = False
    extra_energy_eu: float = 0.0
    drank_litres: float = 0.0


@dataclass(slots=True)
class Microclimate:
    air_temperature_c: float
    light: float
    annual_mean_temperature_c: float
    toxin_level: float
    basking: bool = False
    shaded: bool = False
    in_water: bool = False
    huddling: bool = False
    in_den: bool = False
    brooded_at_c: float | None = None
    crowding: int = 0


@dataclass(slots=True)
class PhysiologyReport:
    excreted_kg: float = 0.0
    assimilated_eu: float = 0.0


class Physiology:
    def __init__(self, ecology: EcologyParameters, mechanics: BodyMechanics, rng: np.random.Generator) -> None:
        self._ecology = ecology
        self._mechanics = mechanics
        self._rng = rng

    def advance(
        self, organism: Organism, activity: ActivityRecord, climate: Microclimate, tick: int, disease_drain: float
    ) -> PhysiologyReport:
        report = PhysiologyReport()
        food_water = self._digest(organism, report)
        thermo_cost, evaporation = self._thermoregulate(organism, climate, tick)
        basal = self._mechanics.basal_rate(organism)
        spent = (
            basal
            + basal * (activity.pal - 1.0) * EFFORT_ENERGY[activity.effort]
            + activity.locomotion_units
            * self._mechanics.locomotion_cost_per_patch(organism)
            * EFFORT_ENERGY[activity.effort]
            + thermo_cost
            + activity.extra_energy_eu
            + self._ecology.disease.parasite_drain_fraction_of_basal * organism.body.parasite_load * basal
            + disease_drain * basal
        )
        self._balance_energy(organism, spent, basal, tick)
        self._balance_water(organism, evaporation, food_water + activity.drank_litres, tick)
        self._grow(organism)
        self._sleep(organism, activity.sleeping, tick)
        self._stamina(organism, activity)
        self._heal(organism, activity.resting or activity.sleeping, basal, tick)
        self._toxins(organism, climate.toxin_level, tick)
        self._parasites(organism, climate.crowding)
        organism.body.pain *= math.exp(-math.log(2.0) / self._ecology.health.pain_half_life_ticks)
        organism.body.stress += STRESS_SMOOTHING * (max(organism.body.fear, organism.body.pain) - organism.body.stress)
        organism.body.damage.fade(DAMAGE_LEDGER_RETENTION)
        organism.body.age_ticks += 1
        return report

    def _digest(self, organism: Organism, report: PhysiologyReport) -> float:
        water = 0.0
        for food_key, amount in list(organism.body.stomach.items()):
            parameters = self._food_parameters(food_key)
            digested = amount * parameters[0]
            efficiency = self.assimilation(organism, food_key)
            report.assimilated_eu += digested * parameters[1] * efficiency
            report.excreted_kg += digested * (1.0 - efficiency)
            water += digested * parameters[2] * LITRES_PER_KG_FOOD_WATER
            remaining = amount - digested
            if remaining < 1e-5:
                del organism.body.stomach[food_key]
            else:
                organism.body.stomach[food_key] = remaining
        organism.body.energy_eu += report.assimilated_eu
        return water

    def assimilation(self, organism: Organism, food_key: str) -> float:
        diet = organism.phenotype.diet
        kidney_cost = 1.0 - WATER_EFFICIENCY_DIGESTION_COST * organism.trait("water_efficiency")
        if food_key == MEAT_KEY:
            gut_cost = 1.0 - CARRION_TOLERANCE_FRESH_MEAT_COST * organism.trait("carrion_tolerance")
            return self._ecology.meat.max_assimilation * math.sqrt(diet.animal) * gut_cost * kidney_cost
        layer = self._ecology.food_layers[food_key]
        efficiency = layer.max_assimilation * math.sqrt(diet.weight(layer.diet_class))
        if food_key == "grass":
            efficiency *= 1.0 - GRAZER_SPECIALIZATION * diet.grazer_browser
        elif food_key == "browse":
            efficiency *= GRAZER_SPECIALIZATION + GRAZER_SPECIALIZATION * diet.grazer_browser
        return efficiency * kidney_cost

    def _food_parameters(self, food_key: str) -> tuple[float, float, float]:
        if food_key == MEAT_KEY:
            meat = self._ecology.meat
            return meat.digestion_rate_per_tick, meat.energy_density_eu_per_kg, meat.water_fraction
        layer = self._ecology.food_layers[food_key]
        return layer.digestion_rate_per_tick, layer.energy_density_eu_per_kg, layer.water_fraction

    def operative_temperature(self, organism: Organism, climate: Microclimate) -> float:
        thermal = self._ecology.thermal
        operative = climate.air_temperature_c
        if climate.in_den:
            operative = (
                thermal.den_air_weight * climate.air_temperature_c
                + (1.0 - thermal.den_air_weight) * climate.annual_mean_temperature_c
            )
        if climate.brooded_at_c is not None:
            brooding = self._ecology.reproduction.brooding_weight
            return brooding * climate.brooded_at_c + (1.0 - brooding) * operative
        if climate.in_den:
            return operative
        if climate.basking:
            operative += thermal.basking_gain_c * climate.light
        if climate.shaded:
            operative -= thermal.shade_cooling_c
        if climate.in_water:
            operative -= thermal.water_cooling_c
        return operative

    def _thermoregulate(self, organism: Organism, climate: Microclimate, tick: int) -> tuple[float, float]:
        thermal = self._ecology.thermal
        body = organism.body
        endothermy = organism.phenotype.endothermy
        operative = self.operative_temperature(organism, climate)
        conductance = allometry.thermal_conductance(body.mass_kg, thermal.conductance_eu_per_c_per_kg05) * (
            1.0 - thermal.insulation_conductance_reduction * organism.trait("insulation")
        )
        if climate.huddling:
            conductance *= HUDDLE_CONDUCTANCE_FACTOR
        basal = self._mechanics.basal_rate(organism)
        lower_critical = thermal.endotherm_set_point_c - basal / max(conductance, 1e-6)
        upper_critical = lower_critical + thermal.thermoneutral_width_c * (1.0 + organism.trait("insulation"))
        cost = endothermy * conductance * max(0.0, lower_critical - operative)
        evaporation = endothermy * thermal.evaporative_water_fraction_per_c * max(0.0, operative - upper_critical)
        starving_cold = body.energy_eu <= 0.0 and operative < lower_critical
        overheating = body.hydration < EVAPORATIVE_FAILURE_HYDRATION and operative > upper_critical
        endotherm_target = operative if (starving_cold or overheating) else thermal.endotherm_set_point_c
        target = endothermy * endotherm_target + (1.0 - endothermy) * operative
        relaxation = endothermy + (1.0 - endothermy) * allometry.thermal_relaxation(
            body.mass_kg, thermal.ectotherm_relaxation_per_tick_per_kg033
        )
        body.body_temperature_c += min(1.0, relaxation) * (target - body.body_temperature_c)
        body.thermal_strain = self._thermal_strain(organism, operative, lower_critical, upper_critical)
        cold_limit, heat_limit = self._mechanics.thermal_limits(organism)
        if body.body_temperature_c < cold_limit:
            body.take_damage(
                "hypothermia", thermal.thermal_damage_per_c_beyond_limit * (cold_limit - body.body_temperature_c), tick
            )
        elif body.body_temperature_c > heat_limit:
            body.take_damage(
                "hyperthermia", thermal.thermal_damage_per_c_beyond_limit * (body.body_temperature_c - heat_limit), tick
            )
        return cost, evaporation

    def _thermal_strain(
        self, organism: Organism, operative: float, lower_critical: float, upper_critical: float
    ) -> float:
        endothermy = organism.phenotype.endothermy
        if operative < lower_critical:
            endotherm_strain = -(lower_critical - operative) / THERMAL_STRAIN_SCALE_C
        elif operative > upper_critical:
            endotherm_strain = (operative - upper_critical) / THERMAL_STRAIN_SCALE_C
        else:
            endotherm_strain = 0.0
        ectotherm_strain = (organism.body.body_temperature_c - organism.trait("thermal_optimum")) / organism.trait(
            "thermal_breadth"
        )
        strain = endothermy * endotherm_strain + (1.0 - endothermy) * ectotherm_strain
        return max(-1.0, min(1.0, strain))

    def _balance_energy(self, organism: Organism, spent: float, basal: float, tick: int) -> None:
        body = organism.body
        metabolism = self._ecology.metabolism
        body.energy_eu -= spent
        capacity = self._mechanics.energy_capacity(organism)
        body.energy_eu = min(body.energy_eu, capacity)
        if body.energy_eu >= 0.0:
            return
        deficit = -body.energy_eu
        body.energy_eu = 0.0
        body.mass_kg = max(
            body.lean_mass_kg * STARVATION_MASS_FLOOR_FRACTION,
            body.mass_kg - deficit / metabolism.lean_energy_density_eu_per_kg,
        )
        body.take_damage(
            "starvation", metabolism.starvation_damage_per_basal_deficit * deficit / max(basal, 1e-6), tick
        )

    def _balance_water(self, organism: Organism, evaporation_fraction: float, gained_litres: float, tick: int) -> None:
        water = self._ecology.water
        body = organism.body
        body_water = self._mechanics.body_water_litres(organism)
        turnover = allometry.water_turnover(body.mass_kg, water.turnover_litres_per_tick_per_kg08)
        loss = turnover * (1.0 - water.efficiency_reduction * organism.trait("water_efficiency"))
        if organism.reproduction.lactating:
            loss *= LACTATION_WATER_MULTIPLIER
        change = (gained_litres - loss) / max(body_water, 1e-6) - evaporation_fraction
        body.hydration = min(1.0, max(0.0, body.hydration + change))
        body.dry_ticks = body.dry_ticks + 1 if body.hydration <= 0.0 else 0
        if body.hydration < water.damaging_hydration:
            body.take_damage("dehydration", water.dehydration_damage_per_tick, tick)

    def _grow(self, organism: Organism) -> None:
        body = organism.body
        adult_mass = organism.phenotype.adult_mass_kg
        if body.lean_mass_kg >= adult_mass:
            return
        capacity = self._mechanics.energy_capacity(organism)
        life = self._ecology.life_history
        floor = life.adult_growth_energy_floor if organism.reproduction.mature else life.juvenile_growth_energy_floor
        spare = body.energy_eu - floor * capacity
        if spare <= 0.0:
            return
        lean_density = (
            self._ecology.metabolism.lean_energy_density_eu_per_kg
            * self._ecology.life_history.construction_energy_discount
        )
        potential = allometry.ontogenetic_growth(
            body.lean_mass_kg, adult_mass, self._ecology.life_history.growth_coefficient_per_tick
        )
        gained = min(potential, spare / lean_density)
        body.lean_mass_kg += gained
        body.mass_kg += gained
        body.energy_eu -= gained * lean_density

    def _sleep(self, organism: Organism, sleeping: bool, tick: int) -> None:
        sleep = self._ecology.sleep
        body = organism.body
        if sleeping:
            body.sleep_pressure *= math.exp(-1.0 / sleep.sleep_time_constant_ticks)
        else:
            body.sleep_pressure = 1.0 - (1.0 - body.sleep_pressure) * math.exp(-1.0 / sleep.wake_time_constant_ticks)

    def _stamina(self, organism: Organism, activity: ActivityRecord) -> None:
        stamina = self._ecology.stamina
        body = organism.body
        if activity.effort >= ALL_OUT_EFFORT:
            body.stamina -= 1.0 / max(organism.phenotype.stamina_ticks, 1.0)
        elif activity.effort == HURRIED_EFFORT:
            body.stamina -= stamina.hurried_cost_per_tick
        else:
            recovery = (
                stamina.rest_recovery_per_tick if activity.resting or activity.sleeping else (stamina.recovery_per_tick)
            )
            body.stamina += recovery
        body.stamina = min(1.0, max(0.0, body.stamina))

    def _heal(self, organism: Organism, resting: bool, basal: float, tick: int) -> None:
        health = self._ecology.health
        body = organism.body
        for wound in body.wounds:
            if wound.bleeding:
                body.take_damage(wound.source, health.bleeding_damage_per_tick, tick)
                stop = health.bleeding_stop_probability * (RESTING_CLOTTING_MULTIPLIER if resting else 1.0)
                wound.bleeding = self._rng.random() >= stop
        fed = self._mechanics.energy_fraction(organism) > FED_ENERGY_FRACTION
        rate = (
            health.healing_per_tick_per_kg_minus025
            * allometry.healing_scale(body.mass_kg)
            * organism.trait("healing_rate")
            * (health.rest_healing_multiplier if resting else 1.0)
            * (1.0 - STRESS_HEALING_PENALTY * body.stress)
        )
        healed = min(1.0 - body.health, rate if fed else rate * UNFED_HEALING_FRACTION)
        if healed <= 0.0:
            return
        body.health += healed
        healing_cost = allometry.kleiber(body.mass_kg, self._ecology.metabolism.healing_cost_eu_per_health_per_kg075)
        body.energy_eu = max(0.0, body.energy_eu - healed * healing_cost)
        for wound in body.wounds:
            wound.severity = max(0.0, wound.severity - healed)
        body.wounds = [wound for wound in body.wounds if wound.severity > 0.0 or wound.bleeding]

    def _toxins(self, organism: Organism, toxin_level: float, tick: int) -> None:
        health = self._ecology.health
        body = organism.body
        resistance = organism.trait("toxin_resistance")
        body.toxin_load = min(
            MAX_TOXIN_LOAD, body.toxin_load + toxin_level * TOXIN_UPTAKE_PER_LEVEL * (1.0 - resistance)
        )
        if body.toxin_load > 0.0:
            body.take_damage(
                "toxin", health.toxin_damage_per_tick_per_load * body.toxin_load * (1.0 - resistance), tick
            )
        body.toxin_load = max(0.0, body.toxin_load - health.toxin_clearance_per_tick)

    def _parasites(self, organism: Organism, crowding: int) -> None:
        disease = self._ecology.disease
        body = organism.body
        body.parasite_load = min(1.0, body.parasite_load + disease.parasite_gain_per_neighbor * crowding)
