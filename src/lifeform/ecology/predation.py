from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np

from lifeform.biology.body import Wound
from lifeform.biology.mechanics import BodyMechanics
from lifeform.biology.organism import Organism
from lifeform.config.parameters import CombatParameters

DAMAGE_JITTER_LOW = 0.7
DAMAGE_JITTER_HIGH = 1.3
BLEEDING_PROBABILITY = 0.6
LIMB_WOUND_PROBABILITY = 0.4
TOXIN_PER_BITE = 0.5
MOB_EFFORT = 1


@dataclass(frozen=True, slots=True)
class StrikeCircumstances:
    effort: int
    surprise: bool = False
    stalked: bool = False
    co_attackers: int = 0
    defender_group: int = 0
    cover: float = 0.0
    braced: bool = False


@dataclass(frozen=True, slots=True)
class StrikeResult:
    probability: float
    hit: bool
    damage: float
    killed: bool


class AttackModel:
    def __init__(self, parameters: CombatParameters, mechanics: BodyMechanics, rng: np.random.Generator) -> None:
        self._parameters = parameters
        self._mechanics = mechanics
        self._rng = rng

    def hit_probability(self, attacker: Organism, defender: Organism, circumstances: StrikeCircumstances) -> float:
        parameters = self._parameters
        attack = self._mechanics.attack_power(attacker, circumstances.effort)
        defense = self._mechanics.defense(defender)
        fatigue_gap = (1.0 - defender.body.stamina) - (1.0 - attacker.body.stamina)
        logit = (
            parameters.bias
            + parameters.power_ratio_weight * math.log(max(attack, 1e-6) / max(defense, 1e-6))
            + parameters.surprise_weight * float(circumstances.surprise)
            + parameters.stalk_weight * float(circumstances.stalked)
            + parameters.pack_weight * circumstances.co_attackers
            - parameters.confusion_weight * math.log1p(circumstances.defender_group)
            - parameters.cover_weight * circumstances.cover
            + parameters.fatigue_weight * fatigue_gap
            - parameters.brace_weight * float(circumstances.braced)
        )
        return 1.0 / (1.0 + math.exp(-logit))

    def strike(
        self, attacker: Organism, defender: Organism, circumstances: StrikeCircumstances, tick: int
    ) -> StrikeResult:
        probability = self.hit_probability(attacker, defender, circumstances)
        if self._rng.random() >= probability:
            return StrikeResult(probability, False, 0.0, False)
        damage = self._damage(attacker, defender, circumstances.effort)
        source = "combat" if attacker.species_id == defender.species_id else "predation"
        defender.body.take_damage(source, damage, tick)
        defender.body.attacked_by = attacker.id
        defender.body.wounds.append(
            Wound(
                damage,
                bool(self._rng.random() < BLEEDING_PROBABILITY),
                bool(self._rng.random() < LIMB_WOUND_PROBABILITY),
                source,
            )
        )
        self._retaliate_passively(attacker, defender, tick)
        attacker.body.toxin_load += TOXIN_PER_BITE * defender.trait("toxicity")
        return StrikeResult(probability, True, damage, defender.body.health <= 0.0)

    def mob(self, mobber: Organism, target: Organism, tick: int) -> float:
        damage = self._parameters.mob_damage_fraction * self._damage(mobber, target, MOB_EFFORT)
        target.body.take_damage("combat", damage, tick)
        target.body.harassed_ticks = 2
        return damage

    def _damage(self, attacker: Organism, defender: Organism, effort: int) -> float:
        raw = self._mechanics.attack_power(attacker, effort) * float(
            self._rng.uniform(DAMAGE_JITTER_LOW, DAMAGE_JITTER_HIGH)
        )
        protected = raw * (1.0 - self._parameters.armor_damage_reduction * defender.trait("armor"))
        return protected / max(self._mechanics.wound_capacity(defender), 1e-6)

    def _retaliate_passively(self, attacker: Organism, defender: Organism, tick: int) -> None:
        spines = defender.trait("weaponry")
        if spines <= 0.0:
            return
        recoil = (
            self._parameters.passive_retaliation_fraction
            * spines
            * self._mechanics.attack_power(defender, 1)
            / max(self._mechanics.wound_capacity(attacker), 1e-6)
        )
        attacker.body.take_damage("retaliation", recoil, tick)
