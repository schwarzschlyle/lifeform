from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel

from lifeform.config.parameters import EcologyParameters
from lifeform.config.world_preset import WorldPreset


class ConfigError(ValueError):
    pass


def deep_merge(base: Mapping[str, Any], override: Mapping[str, Any]) -> dict[str, Any]:
    merged: dict[str, Any] = dict(base)
    for key, value in override.items():
        existing = merged.get(key)
        if isinstance(existing, Mapping) and isinstance(value, Mapping):
            merged[key] = deep_merge(existing, value)
        else:
            merged[key] = value
    return merged


def read_yaml(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as handle:
        content = yaml.safe_load(handle)
    if not isinstance(content, dict):
        raise ConfigError(f"{path} must contain a mapping")
    return content


def config_hash(model: BaseModel) -> str:
    canonical = json.dumps(model.model_dump(mode="json"), sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode()).hexdigest()[:16]


class PresetLibrary:
    def __init__(self, directory: Path) -> None:
        self._directory = directory

    def slugs(self) -> list[str]:
        return sorted(path.stem for path in self._directory.glob("*.yaml"))

    def load(self, slug: str) -> WorldPreset:
        path = self._directory / f"{slug}.yaml"
        if not path.exists():
            raise ConfigError(f"unknown world preset '{slug}' (looked in {self._directory})")
        return WorldPreset.model_validate(read_yaml(path))

    def load_all(self) -> list[WorldPreset]:
        return [self.load(slug) for slug in self.slugs()]


class ArchetypeLibrary:
    def __init__(self, directory: Path) -> None:
        self._directory = directory

    def load(self, slug: str) -> dict[str, Any]:
        path = self._directory / f"{slug}.yaml"
        if not path.exists():
            raise ConfigError(f"unknown archetype '{slug}' (looked in {self._directory})")
        return read_yaml(path)


def ecology_for(preset: WorldPreset) -> EcologyParameters:
    defaults = EcologyParameters().model_dump()
    return EcologyParameters.model_validate(deep_merge(defaults, preset.ecology))
