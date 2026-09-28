from __future__ import annotations

from pathlib import Path
from typing import Literal

from pydantic import Field

from lifeform.config.brains import JEV_BRAIN, SystemOneSettings
from lifeform.config.parameters import FrozenModel

DecisionDetail = Literal["full", "summary", "none"]
SERVED_MODEL_NOTE = "served_model"


class RecordingSettings(FrozenModel):
    chunk_ticks: int = 48
    field_keyframe_interval_ticks: int = 6
    decision_detail: DecisionDetail = "full"


class RunConfig(FrozenModel):
    worlds: tuple[str, ...]
    ticks: int | None = None
    seed: int = 7
    population_scale: float = 1.0
    brain: str = JEV_BRAIN
    system_one: SystemOneSettings = SystemOneSettings()
    recording: RecordingSettings = RecordingSettings()
    max_usd: float | None = None
    max_calls: int | None = None
    output_directory: Path = Path("runs")
    presets_directory: Path = Path("presets")
    archetypes_directory: Path = Path("archetypes")
    run_id: str | None = None
    label: str = ""
    notes: dict[str, str] = Field(default_factory=dict)
