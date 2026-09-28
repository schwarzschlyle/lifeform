from __future__ import annotations

import shutil
from pathlib import Path

import pytest
from pydantic import ValidationError

from lifeform.config.brains import HEURISTIC_BRAIN, OFFLINE_SETTINGS, BrainLibrary
from lifeform.config.loaders import ConfigError

ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture
def library(tmp_path: Path) -> BrainLibrary:
    copy = tmp_path / "brains.yaml"
    shutil.copy(ROOT / "brains.yaml", copy)
    return BrainLibrary(copy)


def test_the_registry_offers_jev_kev_and_the_heuristic(library: BrainLibrary) -> None:
    registry = library.load()
    assert registry.choices == ["jev", "kev", HEURISTIC_BRAIN]
    assert registry.provider("jev").is_jev
    assert not registry.provider("kev").is_jev
    assert registry.settings_for(HEURISTIC_BRAIN) is OFFLINE_SETTINGS


def test_a_named_brain_overrides_the_active_one(library: BrainLibrary) -> None:
    registry = library.load()
    assert registry.resolve(None) == registry.active
    assert registry.resolve("kev") == "kev"
    with pytest.raises(ConfigError):
        registry.resolve("hal")


def test_switching_persists_and_can_switch_back(library: BrainLibrary) -> None:
    assert library.switch("kev").active == "kev"
    assert library.load().active == "kev"
    assert library.load().provider("kev").model == "kev-latest"
    assert library.switch("jev").active == "jev"
    assert library.load().active == "jev"


def test_switching_to_an_unknown_brain_leaves_the_file_alone(library: BrainLibrary) -> None:
    before = library.path.read_text(encoding="utf-8")
    with pytest.raises(ValidationError):
        library.switch("hal")
    assert library.path.read_text(encoding="utf-8") == before
