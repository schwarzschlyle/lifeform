from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from lifeform.catalog.project_catalog import ProjectCatalog
from lifeform.recording.chunks import read_packed

NOT_FOUND = 404


class RunArchive:
    """Read-only access to recorded run bundles, safe against path traversal."""

    def __init__(self, runs_directory: Path) -> None:
        self._root = runs_directory.resolve()

    def list_runs(self) -> list[dict[str, Any]]:
        manifests = sorted(self._root.glob("*/run.json"), reverse=True)
        return [json.loads(manifest.read_text(encoding="utf-8")) for manifest in manifests]

    def run(self, run_id: str) -> dict[str, Any]:
        return self._json(self._safe(run_id, "run.json"))

    def world(self, run_id: str, world: str) -> dict[str, Any]:
        return self._json(self._safe(run_id, "worlds", world, "world.json"))

    def file(self, run_id: str, world: str, path: str) -> FileResponse:
        target = self._safe(run_id, "worlds", world, path)
        return FileResponse(target, headers={"Cache-Control": "no-cache"})

    def decision(self, run_id: str, world: str, tick: int, organism: int) -> dict[str, Any]:
        index = self._json(self._safe(run_id, "worlds", world, "index.json"))
        for start, end, relative in index.get("decisions", []):
            if start <= tick <= end:
                for entry in read_packed(self._safe(run_id, "worlds", world, relative)):
                    if entry["tick"] == tick:
                        return self._find(entry["decisions"], organism)
        raise HTTPException(NOT_FOUND, "no decision recorded for that tick")

    def decision_sample(self, run_id: str, world: str) -> dict[str, Any]:
        """The most eventful decision from the middle of a world's decision tape, as an example of one call."""
        chunks = self._json(self._safe(run_id, "worlds", world, "index.json")).get("decisions", [])
        if not chunks:
            raise HTTPException(NOT_FOUND, "no decisions recorded for that world")
        relative = chunks[len(chunks) // 2][2]
        candidates = [
            (entry["tick"], decision)
            for entry in read_packed(self._safe(run_id, "worlds", world, relative))
            for decision in entry["decisions"]
            if decision.get("state")
        ]
        if not candidates:
            raise HTTPException(NOT_FOUND, "that run did not record decision states")
        tick, decision = max(candidates, key=self._eventfulness)
        return {"tick": tick, "decision": decision}

    @staticmethod
    def _eventfulness(candidate: tuple[int, dict[str, Any]]) -> tuple[float, int]:
        decision = candidate[1]
        return decision["answers"]["threat"]["score"], len(decision["menu"])

    @staticmethod
    def _find(decisions: list[dict[str, Any]], organism: int) -> dict[str, Any]:
        for decision in decisions:
            if decision["id"] == organism:
                return decision
        raise HTTPException(NOT_FOUND, "no decision recorded for that organism")

    def _safe(self, *parts: str) -> Path:
        target = self._root.joinpath(*parts).resolve()
        if self._root not in target.parents or not target.is_file():
            raise HTTPException(NOT_FOUND, "not found")
        return target

    @staticmethod
    def _json(path: Path) -> dict[str, Any]:
        data: dict[str, Any] = json.loads(path.read_text(encoding="utf-8"))
        return data


class CatalogService:
    def __init__(self, presets_directory: Path, archetypes_directory: Path, brains_path: Path) -> None:
        self._catalog = ProjectCatalog(presets_directory, archetypes_directory, brains_path)
        self._cached: dict[str, Any] | None = None

    def catalog(self) -> dict[str, Any]:
        if self._cached is None:
            self._cached = self._catalog.build()
        return {**self._cached, "brains": self._catalog.brains_facts()}


def create_app(
    runs_directory: Path,
    web_directory: Path,
    presets_directory: Path = Path("presets"),
    archetypes_directory: Path = Path("archetypes"),
    brains_path: Path = Path("brains.yaml"),
) -> FastAPI:
    archive = RunArchive(runs_directory)
    catalog = CatalogService(presets_directory, archetypes_directory, brains_path)
    app = FastAPI(title="Lifeform replay server")
    app.add_api_route("/api/catalog", catalog.catalog, methods=["GET"])
    app.add_api_route("/api/runs", archive.list_runs, methods=["GET"])
    app.add_api_route("/api/runs/{run_id}", archive.run, methods=["GET"])
    app.add_api_route("/api/runs/{run_id}/worlds/{world}", archive.world, methods=["GET"])
    app.add_api_route("/api/runs/{run_id}/worlds/{world}/files/{path:path}", archive.file, methods=["GET"])
    app.add_api_route("/api/runs/{run_id}/worlds/{world}/decision", archive.decision, methods=["GET"])
    app.add_api_route("/api/runs/{run_id}/worlds/{world}/decision-sample", archive.decision_sample, methods=["GET"])
    if web_directory.is_dir():
        app.mount("/", StaticFiles(directory=web_directory, html=True), name="theater")
    return app
