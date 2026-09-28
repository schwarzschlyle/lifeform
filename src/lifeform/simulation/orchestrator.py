from __future__ import annotations

import asyncio
import datetime as dt
from dataclasses import dataclass, field
from pathlib import Path
from typing import Protocol

from lifeform.cognition.brain import Brain
from lifeform.cognition.question_panel import PANEL_VERSION
from lifeform.config.loaders import ArchetypeLibrary, PresetLibrary, config_hash
from lifeform.config.run_config import SERVED_MODEL_NOTE, RunConfig
from lifeform.config.world_preset import WorldPreset
from lifeform.recording.chunks import ChunkWriter
from lifeform.recording.world_recorder import WorldRecorder
from lifeform.simulation.budget import DEFAULT_TOKENS_PER_CALL, BudgetGuard, RunEstimate
from lifeform.simulation.engine import PHASE_ORDER, Simulation
from lifeform.simulation.phases.deliberation import DeliberationOptions, DeliberationStalled
from lifeform.simulation.world_factory import WorldFactory


class RunReporter(Protocol):
    def world_started(self, slug: str, title: str, ticks: int, population: int) -> None: ...

    def deliberating(self, slug: str, done: int, total: int) -> None: ...

    def tick_finished(self, slug: str, tick: int, population: int, spent_usd: float, calls: int) -> None: ...

    def world_finished(self, slug: str, status: str, tick: int) -> None: ...


@dataclass(slots=True)
class WorldOutcome:
    slug: str
    title: str
    status: str
    ticks: int
    population: int
    calls: int
    tokens: int


@dataclass(slots=True)
class RunOutcome:
    run_id: str
    directory: Path
    worlds: list[WorldOutcome] = field(default_factory=list)
    calls: int = 0
    tokens: int = 0
    spent_usd: float = 0.0


class RunOrchestrator:
    def __init__(self, config: RunConfig, brain: Brain, reporter: RunReporter, estimate: RunEstimate) -> None:
        self._config = config
        self._brain = brain
        self._reporter = reporter
        self._estimate = estimate
        self._presets = PresetLibrary(config.presets_directory)
        self._factory = WorldFactory(ArchetypeLibrary(config.archetypes_directory))
        self._guard = BudgetGuard(
            config.max_usd,
            config.max_calls,
            config.system_one.price_usd_per_million_input_tokens,
            config.system_one.host_usd_per_hour,
        )

    async def run(self) -> RunOutcome:
        run_id = self._config.run_id or dt.datetime.now().strftime("%Y%m%d-%H%M%S")
        directory = self._config.output_directory / run_id
        outcome = RunOutcome(run_id, directory)
        writer = ChunkWriter(directory)
        presets = [self._presets.load(slug) for slug in self._config.worlds]
        self._write_manifest(writer, outcome, presets, "running")
        try:
            results = await asyncio.gather(
                *(self._run_world(preset, index, directory) for index, preset in enumerate(presets))
            )
            outcome.worlds = list(results)
        finally:
            outcome.calls = self._guard.calls
            outcome.tokens = self._guard.tokens
            outcome.spent_usd = self._guard.spent_usd
            self._write_manifest(writer, outcome, presets, "finished")
        return outcome

    async def _run_world(self, preset: WorldPreset, index: int, directory: Path) -> WorldOutcome:
        config = self._config
        slug = preset.slug
        built = self._factory.build(preset, config.seed + index, config.population_scale)
        simulation = Simulation(
            built,
            self._brain,
            DeliberationOptions(config.system_one.outage_patience_seconds),
            progress=self._progress_callback(slug),
        )
        recorder = WorldRecorder(directory / "worlds" / slug, simulation, config.recording, self._brain.name)
        simulation.observe(recorder)
        recorder.start()
        ticks = config.ticks or preset.default_ticks
        ceiling = max(1, round(preset.targets.max_population * max(config.population_scale, 1.0)))
        self._reporter.world_started(slug, preset.title, ticks, len(simulation.population))
        status = "complete"
        for _ in range(ticks):
            status = self._stop_reason(simulation, ceiling)
            if status != "running":
                break
            try:
                context = await simulation.advance()
            except DeliberationStalled:
                status = "paused_brain_unavailable"
                break
            self._guard.record(
                len(context.decisions), sum(decision.input_tokens for decision in context.decisions.values())
            )
            self._reporter.tick_finished(
                slug, context.tick, len(simulation.population), self._guard.spent_usd, self._guard.calls
            )
        else:
            status = "complete"
        if status == "running":
            status = "complete"
        recorder.finish(status)
        self._reporter.world_finished(slug, status, simulation.tick)
        return WorldOutcome(
            slug, preset.title, status, simulation.tick, len(simulation.population), recorder.calls, recorder.tokens
        )

    def _stop_reason(self, simulation: Simulation, ceiling: int) -> str:
        population = len(simulation.population)
        if population == 0:
            return "extinct"
        if population > ceiling:
            return "population_ceiling"
        tokens_per_call = (self._guard.tokens // self._guard.calls) if self._guard.tokens else DEFAULT_TOKENS_PER_CALL
        if not self._guard.can_afford(population, tokens_per_call):
            return "budget_reached"
        return "running"

    def _progress_callback(self, slug: str) -> ProgressHook:
        return ProgressHook(self._reporter, slug)

    def _brain_facts(self) -> dict[str, object]:
        config = self._config
        settings = config.system_one
        uses_system_one = self._brain.name == settings.name
        return {
            "brain": self._brain.name,
            "brain_title": settings.title if uses_system_one else self._brain.name,
            "is_jev": uses_system_one and settings.is_jev,
            "model": settings.model if uses_system_one else self._brain.name,
            "served_model": config.notes.get(SERVED_MODEL_NOTE, ""),
        }

    def _write_manifest(
        self, writer: ChunkWriter, outcome: RunOutcome, presets: list[WorldPreset], status: str
    ) -> None:
        config = self._config
        estimate = self._estimate
        writer.write_json(
            "run.json",
            {
                "run_id": outcome.run_id,
                "label": config.label,
                "status": status,
                "created": dt.datetime.now().isoformat(timespec="seconds"),
                **self._brain_facts(),
                "panel_version": PANEL_VERSION,
                "phase_order": list(PHASE_ORDER),
                "config_hash": config_hash(config),
                "seed": config.seed,
                "population_scale": config.population_scale,
                "estimate": {
                    "expected_calls": estimate.expected_calls,
                    "expected_usd": round(estimate.expected_usd, 4),
                    "ceiling_usd": round(estimate.ceiling_usd, 4),
                    "expected_hours": round(estimate.expected_hours, 3),
                },
                "totals": {"calls": outcome.calls, "tokens": outcome.tokens, "usd": round(outcome.spent_usd, 4)},
                "worlds": [
                    {
                        "slug": preset.slug,
                        "title": preset.title,
                        "biome": preset.biome,
                        "palette": preset.palette,
                        **self._world_status(outcome, preset.slug),
                    }
                    for preset in presets
                ],
            },
        )

    @staticmethod
    def _world_status(outcome: RunOutcome, slug: str) -> dict[str, object]:
        for world in outcome.worlds:
            if world.slug == slug:
                return {
                    "status": world.status,
                    "ticks": world.ticks,
                    "population": world.population,
                    "calls": world.calls,
                    "tokens": world.tokens,
                }
        return {"status": "running"}


@dataclass(slots=True)
class ProgressHook:
    reporter: RunReporter
    slug: str

    def __call__(self, done: int, total: int) -> None:
        self.reporter.deliberating(self.slug, done, total)
