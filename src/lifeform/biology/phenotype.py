from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np

from lifeform.biology import allometry
from lifeform.biology.genome import GENES, GeneModule, Genome
from lifeform.biology.instincts import INSTINCT_KEYS
from lifeform.config.parameters import EcologyParameters

TEMPERAMENT_TRAITS: tuple[str, ...] = (
    "boldness",
    "curiosity",
    "sociability",
    "aggression",
    "vigilance",
    "patience",
    "altruism",
    "territoriality",
)
SENSE_TRAITS: tuple[str, ...] = ("visual_acuity", "night_vision", "olfaction", "hearing")
DIET_CLASSES: tuple[str, ...] = ("fiber", "soft", "animal")


@dataclass(frozen=True, slots=True)
class DietProfile:
    fiber: float
    soft: float
    animal: float
    grazer_browser: float

    def weight(self, diet_class: str) -> float:
        return float(getattr(self, diet_class))

    @property
    def is_carnivore(self) -> bool:
        return self.animal >= 0.6

    @property
    def is_herbivore(self) -> bool:
        return self.animal < 0.35

    @property
    def dominant(self) -> str:
        return max(DIET_CLASSES, key=self.weight)


@dataclass(frozen=True, slots=True)
class Phenotype:
    traits: dict[str, float]
    diet: DietProfile
    instincts: dict[str, float]
    adult_mass_kg: float
    lifespan_ticks: float
    maturity_ticks: float
    gestation_ticks: float
    weaning_ticks: float
    litter_size: int
    litter_mass_fraction: float
    basal_multiplier: float
    stamina_ticks: float
    decisiveness: float

    def trait(self, name: str) -> float:
        return self.traits[name]

    @property
    def endothermy(self) -> float:
        return self.traits["endothermy"]

    @property
    def activity_phase(self) -> float:
        return self.traits["activity_phase"]


class Development:
    """Builds a phenotype from a genome: developmental noise, allometry and trait costs."""

    def __init__(self, ecology: EcologyParameters, rng: np.random.Generator) -> None:
        self._ecology = ecology
        self._rng = rng

    def develop(self, genome: Genome) -> Phenotype:
        noise = self._rng.normal(0.0, self._ecology.evolution.developmental_noise, GENES.size) * GENES.variation
        developed = np.clip(genome.genotype + noise, 0.0, 1.0)
        traits = {
            spec.name: spec.express(float(developed[index]))
            for index, spec in enumerate(GENES.specs)
            if spec.module not in (GeneModule.INSTINCTS, GeneModule.NEUTRAL)
        }
        instincts = self._expressed_instincts(genome)
        adult_mass = traits["body_mass"] * (1.0 + self._ecology.development.armor_mass_gain * traits["armor"])
        life = self._ecology.life_history
        return Phenotype(
            traits=traits,
            diet=self._diet(traits),
            instincts=instincts,
            adult_mass_kg=adult_mass,
            lifespan_ticks=allometry.quarter_power(adult_mass, life.lifespan_ticks_per_kg025)
            * (life.longevity_base + life.longevity_span * traits["longevity"]),
            maturity_ticks=allometry.quarter_power(adult_mass, life.maturity_ticks_per_kg025)
            * (life.maturity_base - life.maturity_rate_span * traits["maturity_rate"]),
            gestation_ticks=allometry.quarter_power(adult_mass, life.gestation_ticks_per_kg025)
            * (life.gestation_base + life.gestation_precocial_span * traits["precociality"]),
            weaning_ticks=allometry.quarter_power(adult_mass, life.weaning_ticks_per_kg025)
            * (life.weaning_base - life.weaning_precocial_span * traits["precociality"]),
            litter_size=max(
                1, round(life.max_litter_size * (1.0 - traits["offspring_investment"]) ** life.litter_size_exponent)
            ),
            litter_mass_fraction=life.litter_mass_fraction
            * (1.0 + life.precocial_litter_mass_gain * traits["precociality"]),
            basal_multiplier=self._basal_multiplier(traits),
            stamina_ticks=traits["stamina"],
            decisiveness=traits["decisiveness"],
        )

    def _expressed_instincts(self, genome: Genome) -> dict[str, float]:
        threshold = self._ecology.development.instinct_expression_threshold
        genotype = genome.genotype
        expressed: dict[str, float] = {}
        for key in INSTINCT_KEYS:
            value = float(genotype[GENES.index[f"instinct:{key}"]])
            if value > threshold:
                expressed[key] = value
        return expressed

    def _diet(self, traits: dict[str, float]) -> DietProfile:
        sharpness = self._ecology.development.diet_sharpness
        affinities = [traits["fiber_affinity"], traits["soft_plant_affinity"], traits["animal_affinity"]]
        exponentials = [math.exp(sharpness * value) for value in affinities]
        total = sum(exponentials)
        fiber, soft, animal = (value / total for value in exponentials)
        return DietProfile(fiber, soft, animal, traits["grazer_browser"])

    def _basal_multiplier(self, traits: dict[str, float]) -> float:
        costs = self._ecology.metabolism
        trait_costs = (
            costs.weaponry_cost * traits["weaponry"]
            + costs.toxicity_cost * traits["toxicity"]
            + costs.immune_cost * traits["immune_investment"]
            + costs.sense_cost_each * sum(traits[name] for name in SENSE_TRAITS)
            + costs.stamina_cost * GENES.spec("stamina").encode(traits["stamina"])
            + costs.toxin_resistance_cost * traits["toxin_resistance"]
            + costs.attention_cost * traits["attention_span"]
        )
        endothermy_factor = (
            costs.ectotherm_basal_fraction + (1.0 - costs.ectotherm_basal_fraction) * traits["endothermy"]
        )
        return traits["metabolic_scope"] * endothermy_factor * (1.0 + trait_costs)
