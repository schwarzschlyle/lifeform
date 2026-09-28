from __future__ import annotations

import math
from dataclasses import dataclass
from enum import IntFlag

from lifeform.biology.disease import InfectionStage
from lifeform.biology.mechanics import BodyMechanics
from lifeform.biology.organism import Organism
from lifeform.config.parameters import EcologyParameters

HUNGER_RESERVE_WEIGHT = 0.7
HUNGER_STOMACH_WEIGHT = 0.5
THIRST_EXPONENT = 1.5
EXPLORATION_SATURATION_TICKS = 48.0
STARVING_ENERGY_FRACTION = 0.05
DEHYDRATED_HYDRATION = 0.3
POISONED_TOXIN_LOAD = 0.2
INJURED_HEALTH = 0.8
COLD_STRAIN = -0.5
HOT_STRAIN = 0.5
MATE_URGE_BASE = 0.4
MATE_URGE_ENERGY_WEIGHT = 0.6
BREEDING_SEASON_INDEX = 0
SEASONALITY_STRICTNESS = 0.5


class Condition(IntFlag):
    NONE = 0
    ASLEEP = 1 << 0
    HIDDEN = 1 << 1
    IN_DEN = 1 << 2
    CLIMBING = 1 << 3
    SWIMMING = 1 << 4
    PREGNANT = 1 << 5
    LACTATING = 1 << 6
    IN_ESTRUS = 1 << 7
    JUVENILE = 1 << 8
    DEPENDENT = 1 << 9
    INJURED = 1 << 10
    BLEEDING = 1 << 11
    LIMPING = 1 << 12
    POISONED = 1 << 13
    INFECTED_LATENT = 1 << 14
    INFECTED_SICK = 1 << 15
    IMMUNE = 1 << 16
    EXHAUSTED = 1 << 17
    COLD = 1 << 18
    OVERHEATED = 1 << 19
    DEHYDRATED = 1 << 20
    STARVING = 1 << 21
    SENESCENT = 1 << 22
    CARRYING_FOOD = 1 << 23
    BEING_CHASED = 1 << 24
    COURTED = 1 << 25
    RECENTLY_DEFEATED = 1 << 26
    BRACED = 1 << 27
    FROZEN = 1 << 28
    STALKING = 1 << 29
    PLAYING_DEAD = 1 << 30


@dataclass(frozen=True, slots=True)
class DriveState:
    hunger: float
    thirst: float
    sleepiness: float
    thermal: float
    pain: float
    fear: float
    urge_to_mate: float
    social_need: float
    parental_urge: float
    exploratory_urge: float


@dataclass(frozen=True, slots=True)
class SocialSurroundings:
    kin_or_kind_nearby: int
    young_out_of_sight: bool


class ReproductiveClock:
    def __init__(self, ecology: EcologyParameters, mechanics: BodyMechanics) -> None:
        self._parameters = ecology.reproduction
        self._mechanics = mechanics

    def in_breeding_season(self, organism: Organism, season_index: int) -> bool:
        strict = organism.trait("breeding_seasonality") >= SEASONALITY_STRICTNESS
        return season_index == BREEDING_SEASON_INDEX or not strict

    def eligible(self, organism: Organism, season_index: int) -> bool:
        reproduction = organism.reproduction
        if not organism.alive or not reproduction.mature or not self.in_breeding_season(organism, season_index):
            return False
        energy = self._mechanics.energy_fraction(organism)
        if reproduction.is_female:
            nursing_young = reproduction.lactating and bool(reproduction.dependents)
            return (
                reproduction.pregnancy is None
                and not nursing_young
                and energy >= self._parameters.female_energy_threshold
                and organism.body.health >= self._parameters.female_health_threshold
            )
        return energy >= self._parameters.male_energy_threshold and (
            organism.body.health >= self._parameters.male_health_threshold
        )

    def in_estrus(self, organism: Organism, tick: int, season_index: int) -> bool:
        if not organism.reproduction.is_female or not self.eligible(organism, season_index):
            return False
        phase = (tick + organism.reproduction.estrus_offset) % self._parameters.estrus_cycle_ticks
        return phase < self._parameters.estrus_duration_ticks


class DriveCalculator:
    def __init__(self, ecology: EcologyParameters, mechanics: BodyMechanics, clock: ReproductiveClock) -> None:
        self._ecology = ecology
        self._mechanics = mechanics
        self._clock = clock

    def compute(
        self,
        organism: Organism,
        hour: float,
        hours_per_day: float,
        tick: int,
        season_index: int,
        surroundings: SocialSurroundings,
    ) -> DriveState:
        body = organism.body
        energy = self._mechanics.energy_fraction(organism)
        stomach = body.stomach_total() / max(self._mechanics.stomach_capacity(organism), 1e-9)
        hunger = min(1.0, max(0.0, 1.0 - HUNGER_RESERVE_WEIGHT * energy - HUNGER_STOMACH_WEIGHT * stomach))
        thirst = min(1.0, max(0.0, 1.0 - body.hydration**THIRST_EXPONENT))
        return DriveState(
            hunger=hunger,
            thirst=thirst,
            sleepiness=self._sleepiness(organism, hour, hours_per_day),
            thermal=body.thermal_strain,
            pain=body.pain,
            fear=body.fear,
            urge_to_mate=self._urge_to_mate(organism, energy, tick, season_index),
            social_need=organism.trait("sociability") if surroundings.kin_or_kind_nearby == 0 else 0.0,
            parental_urge=organism.trait("parental_care") if surroundings.young_out_of_sight else 0.0,
            exploratory_urge=organism.trait("curiosity")
            * min(1.0, body.ticks_since_novelty / EXPLORATION_SATURATION_TICKS),
        )

    def _sleepiness(self, organism: Organism, hour: float, hours_per_day: float) -> float:
        peak_hour = hours_per_day * organism.phenotype.activity_phase / 2.0
        circadian = math.cos(2.0 * math.pi * (hour - peak_hour) / hours_per_day)
        return min(1.0, max(0.0, organism.body.sleep_pressure - self._ecology.sleep.circadian_weight * circadian))

    def _urge_to_mate(self, organism: Organism, energy: float, tick: int, season_index: int) -> float:
        if not self._clock.eligible(organism, season_index):
            return 0.0
        if organism.reproduction.is_female and not self._clock.in_estrus(organism, tick, season_index):
            return 0.0
        return min(1.0, MATE_URGE_BASE + MATE_URGE_ENERGY_WEIGHT * energy)


class ConditionReader:
    def __init__(self, ecology: EcologyParameters, mechanics: BodyMechanics, clock: ReproductiveClock) -> None:
        self._ecology = ecology
        self._mechanics = mechanics
        self._clock = clock

    def read(self, organism: Organism, tick: int, season_index: int, swimming: bool) -> Condition:
        body = organism.body
        reproduction = organism.reproduction
        flags = Condition.NONE
        checks: tuple[tuple[bool, Condition], ...] = (
            (body.asleep, Condition.ASLEEP),
            (body.hidden, Condition.HIDDEN),
            (body.in_den, Condition.IN_DEN),
            (body.climbing, Condition.CLIMBING),
            (swimming, Condition.SWIMMING),
            (reproduction.pregnancy is not None, Condition.PREGNANT),
            (reproduction.lactating, Condition.LACTATING),
            (self._clock.in_estrus(organism, tick, season_index), Condition.IN_ESTRUS),
            (not reproduction.mature, Condition.JUVENILE),
            (not reproduction.weaned, Condition.DEPENDENT),
            (body.health < INJURED_HEALTH, Condition.INJURED),
            (body.bleeding, Condition.BLEEDING),
            (body.limping, Condition.LIMPING),
            (body.toxin_load > POISONED_TOXIN_LOAD, Condition.POISONED),
            (organism.infection.stage == InfectionStage.EXPOSED, Condition.INFECTED_LATENT),
            (organism.infection.stage == InfectionStage.INFECTIOUS, Condition.INFECTED_SICK),
            (organism.infection.stage == InfectionStage.RECOVERED, Condition.IMMUNE),
            (body.stamina <= 0.0, Condition.EXHAUSTED),
            (body.thermal_strain < COLD_STRAIN, Condition.COLD),
            (body.thermal_strain > HOT_STRAIN, Condition.OVERHEATED),
            (body.hydration < DEHYDRATED_HYDRATION, Condition.DEHYDRATED),
            (self._mechanics.energy_fraction(organism) < STARVING_ENERGY_FRACTION, Condition.STARVING),
            (self._mechanics.is_senescent(organism), Condition.SENESCENT),
            (body.carrying is not None, Condition.CARRYING_FOOD),
            (body.chased_by is not None, Condition.BEING_CHASED),
            (bool(reproduction.courted_by), Condition.COURTED),
            (organism.social.defeated_until_tick >= tick, Condition.RECENTLY_DEFEATED),
            (body.braced, Condition.BRACED),
            (body.frozen, Condition.FROZEN),
            (body.stalking, Condition.STALKING),
            (body.playing_dead, Condition.PLAYING_DEAD),
        )
        for active, flag in checks:
            if active:
                flags |= flag
        return flags
