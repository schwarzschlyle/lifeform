from __future__ import annotations

import math
from dataclasses import dataclass
from enum import StrEnum
from typing import Literal

import numpy as np
import numpy.typing as npt

from lifeform.biology.instincts import INSTINCT_KEYS

Scale = Literal["linear", "log"]
AlleleArray = npt.NDArray[np.float32]


class GeneModule(StrEnum):
    MORPHOLOGY = "morphology"
    LOCOMOTION = "locomotion"
    PHYSIOLOGY = "physiology"
    DIET = "diet"
    SENSES = "senses"
    LIFE_HISTORY = "life_history"
    TEMPERAMENT = "temperament"
    DECISION_STYLE = "decision_style"
    COGNITION = "cognition"
    META = "meta"
    INSTINCTS = "instincts"
    NEUTRAL = "neutral"


@dataclass(frozen=True, slots=True)
class GeneSpec:
    name: str
    module: GeneModule
    low: float = 0.0
    high: float = 1.0
    scale: Scale = "linear"
    distance_weight: float = 1.0
    variation: float = 1.0

    def express(self, allele_value: float) -> float:
        clipped = min(max(allele_value, 0.0), 1.0)
        if self.scale == "log":
            return math.exp(math.log(self.low) + (math.log(self.high) - math.log(self.low)) * clipped)
        return self.low + (self.high - self.low) * clipped

    def encode(self, phenotype_value: float) -> float:
        if self.scale == "log":
            fraction = (math.log(phenotype_value) - math.log(self.low)) / (math.log(self.high) - math.log(self.low))
        else:
            fraction = (phenotype_value - self.low) / (self.high - self.low)
        return min(max(fraction, 0.0), 1.0)


def _module(module: GeneModule, *specs: tuple[str, float, float, Scale]) -> list[GeneSpec]:
    return [GeneSpec(name, module, low, high, scale) for name, low, high, scale in specs]


def _unit(module: GeneModule, *names: str) -> list[GeneSpec]:
    return [GeneSpec(name, module) for name in names]


_SPECS: list[GeneSpec] = [
    GeneSpec("body_mass", GeneModule.MORPHOLOGY, 0.2, 400.0, "log", variation=0.3),
    *_unit(GeneModule.MORPHOLOGY, "limb_ratio", "armor", "weaponry", "insulation"),
    *_module(GeneModule.MORPHOLOGY, ("fat_capacity", 0.03, 0.35, "linear")),
    *_unit(GeneModule.MORPHOLOGY, "crypsis", "ornament", "toxicity", "coat_hue", "pattern"),
    *_unit(GeneModule.LOCOMOTION, "swim_skill", "climb_skill", "dig_skill"),
    *_module(GeneModule.LOCOMOTION, ("stamina", 1.0, 6.0, "linear")),
    *_unit(GeneModule.PHYSIOLOGY, "endothermy"),
    *_module(
        GeneModule.PHYSIOLOGY,
        ("thermal_optimum", 10.0, 40.0, "linear"),
        ("thermal_breadth", 4.0, 20.0, "linear"),
        ("metabolic_scope", 0.7, 1.4, "linear"),
    ),
    *_unit(GeneModule.PHYSIOLOGY, "water_efficiency", "toxin_resistance", "immune_investment"),
    *_module(GeneModule.PHYSIOLOGY, ("healing_rate", 0.5, 2.0, "linear")),
    *_unit(GeneModule.PHYSIOLOGY, "carrion_tolerance", "longevity"),
    *_unit(GeneModule.DIET, "fiber_affinity", "soft_plant_affinity", "animal_affinity", "grazer_browser"),
    *_unit(GeneModule.SENSES, "visual_acuity", "night_vision", "olfaction", "hearing", "vocal_capacity"),
    *_unit(
        GeneModule.LIFE_HISTORY,
        "maturity_rate",
        "offspring_investment",
        "precociality",
        "parental_care",
        "breeding_seasonality",
        "mate_choosiness",
    ),
    *_unit(
        GeneModule.TEMPERAMENT,
        "boldness",
        "curiosity",
        "sociability",
        "aggression",
        "vigilance",
        "patience",
        "altruism",
        "territoriality",
        "activity_phase",
    ),
    *_module(GeneModule.DECISION_STYLE, ("decisiveness", 1.0, 6.0, "linear")),
    *_unit(GeneModule.DECISION_STYLE, "caution"),
    *_module(GeneModule.COGNITION, ("learning_rate", 0.05, 0.6, "linear")),
    *_unit(GeneModule.COGNITION, "memory_capacity", "attention_span"),
    *_module(GeneModule.META, ("mutation_modifier", 0.5, 2.0, "linear")),
    *_unit(GeneModule.META, "dispersal", "sex_ratio_bias"),
    *[GeneSpec(f"instinct:{key}", GeneModule.INSTINCTS) for key in INSTINCT_KEYS],
    *[GeneSpec(f"marker:{index}", GeneModule.NEUTRAL) for index in range(1, 9)],
]


class GeneCatalog:
    def __init__(self, specs: list[GeneSpec]) -> None:
        self.specs = tuple(specs)
        self.index = {spec.name: position for position, spec in enumerate(self.specs)}
        self.size = len(self.specs)
        self.modules = {
            module: [position for position, spec in enumerate(self.specs) if spec.module == module]
            for module in GeneModule
        }
        self.distance_weights = np.array([spec.distance_weight for spec in self.specs], dtype=np.float32)
        self.variation = np.array([spec.variation for spec in self.specs], dtype=np.float32)

    def spec(self, name: str) -> GeneSpec:
        return self.specs[self.index[name]]

    def neutral_indices(self) -> list[int]:
        return self.modules[GeneModule.NEUTRAL]

    def trait_indices(self) -> list[int]:
        return [
            position
            for position, spec in enumerate(self.specs)
            if spec.module not in (GeneModule.NEUTRAL, GeneModule.INSTINCTS)
        ]


GENES = GeneCatalog(_SPECS)


class Genome:
    """Diploid additive genome: two alleles per locus, each in [0, 1] gene space."""

    def __init__(self, alleles: AlleleArray) -> None:
        if alleles.shape != (2, GENES.size):
            raise ValueError(f"genome must have shape (2, {GENES.size}), got {alleles.shape}")
        self.alleles = np.clip(alleles, 0.0, 1.0).astype(np.float32)

    @property
    def genotype(self) -> AlleleArray:
        return self.alleles.mean(axis=0).astype(np.float32)

    def gene(self, name: str) -> float:
        return float(self.genotype[GENES.index[name]])

    def expressed(self, name: str) -> float:
        return GENES.spec(name).express(self.gene(name))

    def distance(self, other: Genome) -> float:
        difference = self.genotype - other.genotype
        weights = GENES.distance_weights
        return float(np.sqrt(np.sum(weights * difference**2) / np.sum(weights)))

    def copy(self) -> Genome:
        return Genome(self.alleles.copy())


def genotype_distance(first: AlleleArray, second: AlleleArray) -> float:
    weights = GENES.distance_weights
    return float(np.sqrt(np.sum(weights * (first - second) ** 2) / np.sum(weights)))
