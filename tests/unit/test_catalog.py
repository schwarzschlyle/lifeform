from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

from lifeform.actions.verbs import Verb
from lifeform.biology.genome import GENES, GeneModule
from lifeform.catalog.notes import DEATH_NOTES, GENE_NOTES, MODULE_NOTES, PHASE_NOTES, VERB_NOTES
from lifeform.catalog.project_catalog import ProjectCatalog
from lifeform.ecology.mortality import DeathCause
from lifeform.recording.chunks import ChunkWriter
from lifeform.server.app import create_app
from lifeform.simulation.engine import PHASE_ORDER

ROOT = Path(__file__).resolve().parents[2]
UNDESCRIBED_MODULES = (GeneModule.INSTINCTS, GeneModule.NEUTRAL)
DIET_TOLERANCE = 1e-2
OK = 200
NOT_FOUND = 404


@pytest.fixture(scope="module")
def catalog() -> dict[str, Any]:
    return ProjectCatalog(ROOT / "presets", ROOT / "archetypes", ROOT / "brains.yaml").build()


def test_every_described_thing_has_a_note() -> None:
    trait_genes = {spec.name for spec in GENES.specs if spec.module not in UNDESCRIBED_MODULES}
    assert trait_genes <= GENE_NOTES.keys()
    assert set(Verb) == VERB_NOTES.keys()
    assert set(DeathCause) == DEATH_NOTES.keys()
    assert set(PHASE_ORDER) <= PHASE_NOTES.keys()
    assert {module.value for module in GeneModule} == MODULE_NOTES.keys()


def test_catalog_covers_every_archetype_world_and_locus(catalog: dict[str, Any]) -> None:
    assert len(catalog["archetypes"]) == len(list((ROOT / "archetypes").glob("*.yaml")))
    assert len(catalog["worlds"]) == len(list((ROOT / "presets").glob("*.yaml")))
    assert len(catalog["genes"]) == GENES.size
    assert [question["key"] for question in catalog["panel"]["questions"]] == [
        "action",
        "effort",
        "threat",
        "call",
        "focus",
    ]


def test_species_facts_are_physically_sensible(catalog: dict[str, Any]) -> None:
    for archetype in catalog["archetypes"]:
        stats = archetype["stats"]
        assert stats["adult_mass_kg"] > 0.0
        assert stats["lifespan_days"] > stats["maturity_days"] > 0.0
        assert stats["litter_size"] >= 1
        assert stats["vision_day_patches"] >= stats["vision_night_patches"]
        assert abs(sum(archetype["diet"].values()) - 1.0) < DIET_TOLERANCE
        assert archetype["worlds"], f"{archetype['slug']} founds no world"


def test_server_serves_catalog_and_a_sample_decision(tmp_path: Path) -> None:
    world = tmp_path / "runs" / "run-a" / "worlds" / "tiny"
    writer = ChunkWriter(world)
    calm = _decision(1, threat=0.2)
    alarmed = _decision(2, threat=3.4)
    writer.write_packed(
        "decisions/000000-000001.msgpack.gz",
        [
            {"tick": 0, "decisions": [calm]},
            {"tick": 1, "decisions": [alarmed]},
        ],
    )
    writer.write_json("index.json", {"decisions": [[0, 1, "decisions/000000-000001.msgpack.gz"]]})
    client = TestClient(
        create_app(tmp_path / "runs", tmp_path / "web", ROOT / "presets", ROOT / "archetypes", ROOT / "brains.yaml")
    )

    assert client.get("/api/catalog").status_code == OK
    sample = client.get("/api/runs/run-a/worlds/tiny/decision-sample")
    assert sample.status_code == OK
    assert sample.json() == {"tick": 1, "decision": alarmed}
    assert client.get("/api/runs/run-a/worlds/missing/decision-sample").status_code == NOT_FOUND


def _decision(organism: int, threat: float) -> dict[str, Any]:
    return {
        "id": organism,
        "menu": [["rest", "rest where you are"]],
        "answers": {"threat": {"score": threat, "probabilities": {}}},
        "state": {"task": "one moment"},
    }
