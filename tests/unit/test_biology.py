from __future__ import annotations

import numpy as np
import pytest

from lifeform.biology import allometry
from lifeform.biology.genome import GENES, Genome
from lifeform.biology.inheritance import Inheritance
from lifeform.biology.lineage import Lineage
from lifeform.cognition.vocabulary import HUNGER, temperament_word
from lifeform.config.parameters import EcologyParameters, EvolutionParameters


def test_genome_has_89_loci() -> None:
    assert GENES.size == 89
    assert len(GENES.neutral_indices()) == 8


@pytest.mark.parametrize(("name", "value"), [("body_mass", 40.0), ("stamina", 4.0), ("thermal_optimum", 24.0)])
def test_gene_encoding_round_trips(name: str, value: float) -> None:
    spec = GENES.spec(name)
    assert spec.express(spec.encode(value)) == pytest.approx(value, rel=1e-6)


def test_offspring_alleles_stay_in_range() -> None:
    rng = np.random.default_rng(0)
    parents = [Genome(rng.random((2, GENES.size)).astype(np.float32)) for _ in range(2)]
    inheritance = Inheritance(EvolutionParameters(mutation_probability=0.5), rng)
    for _ in range(50):
        child = inheritance.offspring(parents[0], parents[1])
        assert child.alleles.min() >= 0.0
        assert child.alleles.max() <= 1.0


def test_identical_genomes_have_zero_distance() -> None:
    genome = Genome(np.full((2, GENES.size), 0.4, dtype=np.float32))
    assert genome.distance(genome.copy()) == 0.0


def test_relatedness_follows_the_pedigree() -> None:
    mother, father, other = Lineage.founder(1), Lineage.founder(2), Lineage.founder(3)
    first = Lineage.offspring(10, mother, father)
    second = Lineage.offspring(11, mother, father)
    half = Lineage.offspring(12, mother, other)
    assert first.relatedness(second) == pytest.approx(0.5)
    assert first.relatedness(half) == pytest.approx(0.25)
    assert first.relatedness(mother) == pytest.approx(0.5)
    cousin_a = Lineage.offspring(20, first, Lineage.founder(4))
    cousin_b = Lineage.offspring(21, second, Lineage.founder(5))
    assert cousin_a.relatedness(cousin_b) == pytest.approx(0.125)


def test_kleiber_scaling() -> None:
    assert allometry.kleiber(16.0, 1.0) == pytest.approx(8.0)
    assert allometry.ontogenetic_growth(10.0, 10.0, 0.1) == 0.0


def test_numbers_become_words() -> None:
    assert HUNGER.word(0.9) == "starving"
    assert HUNGER.word(0.0) == "not hungry"
    assert temperament_word("boldness", 0.5) is None
    assert temperament_word("boldness", 0.05) == "very timid"


def test_ecology_parameters_reject_unstable_diffusion() -> None:
    with pytest.raises(ValueError, match="stable"):
        EcologyParameters.model_validate({"scent": {"diffusion": 0.4}})
