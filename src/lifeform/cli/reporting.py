from __future__ import annotations

from rich.console import Console
from rich.progress import BarColumn, MofNCompleteColumn, Progress, TaskID, TextColumn, TimeElapsedColumn
from rich.table import Table

from lifeform.config.brains import HEURISTIC_BRAIN, OFFLINE_SETTINGS, BrainRegistry, SystemOneSettings
from lifeform.config.world_preset import WorldPreset
from lifeform.simulation.budget import RunEstimate
from lifeform.simulation.orchestrator import RunOutcome


class ConsoleReporter:
    """Shows one progress bar per world plus the decisions still in flight for the current tick."""

    def __init__(self, console: Console) -> None:
        self._console = console
        self._progress = Progress(
            TextColumn("[bold]{task.description}"),
            BarColumn(),
            MofNCompleteColumn(),
            TextColumn("{task.fields[detail]}"),
            TimeElapsedColumn(),
            console=console,
        )
        self._tasks: dict[str, TaskID] = {}
        self._details: dict[str, str] = {}

    def __enter__(self) -> ConsoleReporter:
        self._progress.start()
        return self

    def __exit__(self, *_: object) -> None:
        self._progress.stop()

    def world_started(self, slug: str, title: str, ticks: int, population: int) -> None:
        self._tasks[slug] = self._progress.add_task(title, total=ticks, detail=f"{population} animals")

    def deliberating(self, slug: str, done: int, total: int) -> None:
        base = self._details.get(slug, "")
        self._progress.update(self._tasks[slug], detail=f"{base}  thinking {done}/{total}")

    def tick_finished(self, slug: str, tick: int, population: int, spent_usd: float, calls: int) -> None:
        self._details[slug] = f"{population} animals · {calls:,} calls · ${spent_usd:,.4f}"
        self._progress.update(self._tasks[slug], completed=tick, detail=self._details[slug])

    def world_finished(self, slug: str, status: str, tick: int) -> None:
        self._progress.update(self._tasks[slug], detail=f"{self._details.get(slug, '')}  [{status}]")


def world_table(presets: list[WorldPreset]) -> Table:
    table = Table(title="Lifeform worlds")
    for column in ("slug", "title", "biome", "grid", "founders", "default ticks", "stretch"):
        table.add_column(column)
    for preset in presets:
        table.add_row(
            preset.slug,
            preset.title,
            preset.biome,
            f"{preset.grid.width}×{preset.grid.height}",
            str(preset.founder_count),
            f"{preset.default_ticks:,}",
            "yes" if preset.stretch else "",
        )
    return table


def estimate_table(estimate: RunEstimate, brain_title: str) -> Table:
    table = Table(title=f"{brain_title} cost estimate (one call per living animal per tick)")
    for column in ("world", "ticks", "founders", "expected animals", "expected calls", "expected $", "ceiling $"):
        table.add_column(column, justify="right" if column != "world" else "left")
    price = estimate.price_per_million
    tokens = estimate.tokens_per_call
    for world in estimate.worlds:
        table.add_row(
            world.title,
            f"{world.ticks:,}",
            str(world.founders),
            f"{world.expected_mean_organisms:,.0f}",
            f"{world.expected_calls:,}",
            f"${world.expected_usd(tokens, price):,.2f}",
            f"${world.ceiling_usd(tokens, price):,.2f}",
        )
    table.add_row(
        "[bold]total",
        "",
        "",
        "",
        f"[bold]{estimate.expected_calls:,}",
        f"[bold]${estimate.expected_usd:,.2f}",
        f"[bold]${estimate.ceiling_usd:,.2f}",
    )
    return table


def brain_table(registry: BrainRegistry) -> Table:
    table = Table(title="Brains (the model that makes every animal's decisions)")
    for column in ("", "brain", "model", "endpoint", "price", "about"):
        table.add_column(column)
    for settings in [*registry.providers.values(), OFFLINE_SETTINGS]:
        table.add_row(
            "[green]●[/green]" if settings.name == registry.active else "",
            f"[bold]{settings.name}[/bold]",
            settings.model,
            settings.base_url or "offline",
            _price_text(settings),
            settings.description,
        )
    return table


def _price_text(settings: SystemOneSettings) -> str:
    if settings.name == HEURISTIC_BRAIN:
        return "free"
    parts = []
    if settings.price_usd_per_million_input_tokens > 0.0:
        parts.append(f"${settings.price_usd_per_million_input_tokens:g}/M tokens")
    if settings.host_usd_per_hour > 0.0:
        parts.append(f"${settings.host_usd_per_hour:g}/h hosting")
    return " + ".join(parts) or "no per-call price"


def outcome_table(outcome: RunOutcome) -> Table:
    table = Table(title=f"Run {outcome.run_id}")
    for column in ("world", "status", "ticks", "animals alive", "calls", "tokens"):
        table.add_column(column)
    for world in outcome.worlds:
        table.add_row(
            world.title,
            world.status,
            f"{world.ticks:,}",
            str(world.population),
            f"{world.calls:,}",
            f"{world.tokens:,}",
        )
    return table
