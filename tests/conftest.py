from __future__ import annotations

from pathlib import Path

import pytest

from lifeform.config.loaders import ArchetypeLibrary, PresetLibrary
from lifeform.simulation.world_factory import BuiltWorld, WorldFactory

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def presets() -> PresetLibrary:
    return PresetLibrary(ROOT / "presets")


@pytest.fixture
def factory() -> WorldFactory:
    return WorldFactory(ArchetypeLibrary(ROOT / "archetypes"))


@pytest.fixture
def small_world(presets: PresetLibrary, factory: WorldFactory) -> BuiltWorld:
    return factory.build(presets.load("red-queen-pit"), seed=3, population_scale=0.3)
