from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml
from pydantic import model_validator

from lifeform.config.loaders import ConfigError, read_yaml
from lifeform.config.parameters import FrozenModel

HEURISTIC_BRAIN = "heuristic"
JEV_BRAIN = "jev"
UNAUTHENTICATED_KEY = "local"


class SystemOneSettings(FrozenModel):
    """One TypeSafe System One endpoint that can decide for the animals: Jev itself, or a compatible model like Kev."""

    name: str = JEV_BRAIN
    title: str = "Jev"
    description: str = "TypeSafe AI's hosted System One model."
    setup_hint: str = ""
    base_url: str = "https://api.typesafe.ai"
    model: str = "jev-1.13.0"
    api_key_env: str = "TYPESAFE_API_KEY"
    api_key_required: bool = True
    requests_per_minute: int = 1200
    tokens_per_second: int = 250_000
    price_usd_per_million_input_tokens: float = 0.042
    host_usd_per_hour: float = 0.0
    governor_start_fraction: float = 0.9
    max_in_flight: int = 32
    request_timeout_seconds: float = 5.0
    max_retries: int = 4
    retry_budget_seconds: float = 60.0
    outage_patience_seconds: float = 600.0

    @property
    def is_jev(self) -> bool:
        return self.name == JEV_BRAIN


OFFLINE_SETTINGS = SystemOneSettings(
    name=HEURISTIC_BRAIN,
    title="Heuristic stand-in",
    description="Offline development stand-in with no model behind it. Its runs are never Jev or Kev results.",
    base_url="",
    model=HEURISTIC_BRAIN,
    api_key_env="",
    api_key_required=False,
    price_usd_per_million_input_tokens=0.0,
    host_usd_per_hour=0.0,
)


class BrainRegistry(FrozenModel):
    """The decision models a run can use, and which one runs when none is named."""

    active: str
    providers: dict[str, SystemOneSettings]

    @model_validator(mode="before")
    @classmethod
    def _name_providers_by_key(cls, data: Any) -> Any:
        if isinstance(data, dict) and isinstance(data.get("providers"), dict):
            data = {**data, "providers": {key: {**value, "name": key} for key, value in data["providers"].items()}}
        return data

    @model_validator(mode="after")
    def _active_is_known(self) -> BrainRegistry:
        if self.active not in self.choices:
            raise ValueError(f"active brain '{self.active}' is not one of {', '.join(self.choices)}")
        return self

    @property
    def choices(self) -> list[str]:
        return [*self.providers, HEURISTIC_BRAIN]

    def provider(self, name: str) -> SystemOneSettings:
        if name not in self.providers:
            raise ConfigError(f"unknown brain '{name}'; choose one of {', '.join(self.choices)}")
        return self.providers[name]

    def settings_for(self, name: str) -> SystemOneSettings:
        return OFFLINE_SETTINGS if name == HEURISTIC_BRAIN else self.provider(name)

    def resolve(self, requested: str | None) -> str:
        chosen = requested or self.active
        if chosen not in self.choices:
            raise ConfigError(f"unknown brain '{chosen}'; choose one of {', '.join(self.choices)}")
        return chosen


class BrainLibrary:
    """Reads and switches the brain registry file (brains.yaml)."""

    def __init__(self, path: Path) -> None:
        self._path = path

    @property
    def path(self) -> Path:
        return self._path

    def load(self) -> BrainRegistry:
        if not self._path.exists():
            raise ConfigError(f"brain registry {self._path} not found")
        return BrainRegistry.model_validate(read_yaml(self._path))

    def switch(self, name: str) -> BrainRegistry:
        content = read_yaml(self._path)
        switched = BrainRegistry.model_validate({**content, "active": name})
        self._path.write_text(yaml.safe_dump({**content, "active": name}, sort_keys=False), encoding="utf-8")
        return switched
