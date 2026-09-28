from __future__ import annotations

import numpy as np

from lifeform.biology.phenotype import Phenotype

ONSETS: tuple[str, ...] = ("t", "k", "v", "s", "m", "n", "r", "l", "p", "b", "d", "sh", "th", "z", "h", "f", "y")
NUCLEI: tuple[str, ...] = ("a", "e", "i", "o", "u", "ai", "ea", "ou", "y")
CODAS: tuple[str, ...] = ("", "", "", "n", "l", "r", "s", "sh", "k", "m")

HUE_WORDS: tuple[str, ...] = (
    "Rust",
    "Amber",
    "Gold",
    "Moss",
    "Fern",
    "Teal",
    "Frost",
    "Dusk",
    "Plum",
    "Rose",
    "Ash",
    "Ember",
)
PATTERN_SUFFIXES: tuple[str, ...] = ("back", "-spotted", "-striped")


class IndividualNamer:
    def __init__(self, rng: np.random.Generator) -> None:
        self._rng = rng

    def name(self) -> str:
        syllable_count = int(self._rng.integers(2, 4))
        name = "".join(self._syllable() for _ in range(syllable_count))
        return name.capitalize()

    def _syllable(self) -> str:
        return str(self._rng.choice(ONSETS)) + str(self._rng.choice(NUCLEI)) + str(self._rng.choice(CODAS))


class SpeciesNamer:
    def __init__(self) -> None:
        self._used: dict[str, int] = {}

    def name(self, phenotype: Phenotype) -> str:
        hue = HUE_WORDS[int(phenotype.trait("coat_hue") * len(HUE_WORDS)) % len(HUE_WORDS)]
        suffix = PATTERN_SUFFIXES[
            min(int(phenotype.trait("pattern") * len(PATTERN_SUFFIXES)), len(PATTERN_SUFFIXES) - 1)
        ]
        base = f"{hue}{suffix} {self._niche_noun(phenotype)}"
        count = self._used.get(base, 0) + 1
        self._used[base] = count
        return base if count == 1 else f"{base} {self._roman(count)}"

    @staticmethod
    def _niche_noun(phenotype: Phenotype) -> str:
        diet = phenotype.diet
        mass = phenotype.adult_mass_kg
        if phenotype.trait("swim_skill") > 0.65:
            return "Wader"
        if phenotype.trait("armor") > 0.65 and phenotype.endothermy < 0.4:
            return "Crawler"
        if diet.dominant == "animal":
            if mass < 3.0:
                return "Snuffler"
            if phenotype.trait("stamina") > 3.5:
                return "Runner"
            return "Stalker" if phenotype.trait("weaponry") > 0.5 else "Scavenger"
        if diet.dominant == "fiber":
            if mass < 5.0:
                return "Hopper"
            return "Browser" if diet.grazer_browser > 0.55 else "Grazer"
        return "Hopper" if mass < 3.0 else "Forager"

    @staticmethod
    def _roman(number: int) -> str:
        numerals = ((10, "X"), (9, "IX"), (5, "V"), (4, "IV"), (1, "I"))
        result = ""
        for value, symbol in numerals:
            while number >= value:
                result += symbol
                number -= value
        return result
