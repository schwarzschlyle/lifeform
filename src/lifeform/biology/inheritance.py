from __future__ import annotations

import numpy as np

from lifeform.biology.genome import GENES, AlleleArray, Genome
from lifeform.config.parameters import EvolutionParameters


class Recombination:
    def __init__(self, parameters: EvolutionParameters, rng: np.random.Generator) -> None:
        self._parameters = parameters
        self._rng = rng

    def gamete(self, parent: Genome) -> AlleleArray:
        gamete = np.empty(GENES.size, dtype=np.float32)
        for indices in GENES.modules.values():
            strand = int(self._rng.integers(2))
            for locus in indices:
                if self._rng.random() < self._parameters.linkage_switch_probability:
                    strand = 1 - strand
                gamete[locus] = parent.alleles[strand, locus]
        return gamete


class Mutation:
    def __init__(self, parameters: EvolutionParameters, rng: np.random.Generator) -> None:
        self._parameters = parameters
        self._rng = rng

    def apply(self, gamete: AlleleArray, mutation_modifier: float) -> AlleleArray:
        parameters = self._parameters
        mutated = gamete.copy()
        hits = self._rng.random(GENES.size) < parameters.mutation_probability * mutation_modifier
        large = self._rng.random(GENES.size) < parameters.large_mutation_fraction
        sigma = np.where(large, parameters.large_mutation_sigma, parameters.mutation_sigma) * GENES.variation
        mutated[hits] += self._rng.normal(0.0, sigma[hits]).astype(np.float32)
        fixed = GENES.index["sex_ratio_bias"]
        mutated[fixed] = gamete[fixed]
        return np.clip(mutated, 0.0, 1.0).astype(np.float32)


class Inheritance:
    def __init__(self, parameters: EvolutionParameters, rng: np.random.Generator) -> None:
        self._recombination = Recombination(parameters, rng)
        self._mutation = Mutation(parameters, rng)

    def offspring(self, mother: Genome, father: Genome) -> Genome:
        maternal = self._mutation.apply(self._recombination.gamete(mother), mother.expressed("mutation_modifier"))
        paternal = self._mutation.apply(self._recombination.gamete(father), father.expressed("mutation_modifier"))
        return Genome(np.stack([maternal, paternal]))
