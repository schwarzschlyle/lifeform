from __future__ import annotations

import asyncio
import json
import os
from pathlib import Path
from typing import Annotated

import typer
import uvicorn
from rich.console import Console

from lifeform.adapters.offline import HeuristicBrain
from lifeform.adapters.system_one.brain import SystemOneBrain
from lifeform.adapters.system_one.codec import PanelCodec
from lifeform.adapters.system_one.gateway import SystemOneGateway
from lifeform.adapters.system_one.rate_governor import RateGovernor
from lifeform.cli.reporting import ConsoleReporter, brain_table, estimate_table, outcome_table, world_table
from lifeform.cognition.brain import Brain, BrainMisuse, BrainUnavailable
from lifeform.config.brains import (
    HEURISTIC_BRAIN,
    UNAUTHENTICATED_KEY,
    BrainLibrary,
    BrainRegistry,
    SystemOneSettings,
)
from lifeform.config.loaders import ConfigError, PresetLibrary
from lifeform.config.run_config import SERVED_MODEL_NOTE, DecisionDetail, RecordingSettings, RunConfig
from lifeform.config.world_preset import WorldPreset
from lifeform.server.app import create_app
from lifeform.simulation.budget import DEFAULT_TOKENS_PER_CALL, MINUTES_PER_HOUR, CostEstimator, RunEstimate
from lifeform.simulation.orchestrator import RunOrchestrator, RunOutcome

ALL_CORE_WORLDS = "all"
ALL_WORLDS = "everything"
DECISION_DETAILS: tuple[DecisionDetail, ...] = ("full", "summary", "none")

app = typer.Typer(
    help="Lifeform: an artificial ecology where every animal decides with one System One call (Jev or Kev) per tick.",
    no_args_is_help=True,
)
console = Console()

WorldsArgument = Annotated[
    list[str] | None,
    typer.Argument(help="World slugs, or 'all' for the 12 core worlds, or 'everything' to include stretch worlds."),
]
TicksOption = Annotated[int | None, typer.Option("--ticks", "-t", help="Ticks per world (default: each preset's).")]
ScaleOption = Annotated[
    float, typer.Option("--population-scale", "-p", help="Multiply founder counts and population targets.")
]
PresetsOption = Annotated[Path, typer.Option("--presets", help="Directory of world presets.")]
BrainsOption = Annotated[
    Path, typer.Option("--brains", help="Brain registry file (which models exist, which is active).")
]
BrainOption = Annotated[
    str | None,
    typer.Option("--brain", "-b", help="jev, kev or heuristic. Default: the active brain in brains.yaml."),
]


def _library(presets: Path) -> PresetLibrary:
    return PresetLibrary(presets)


def _registry(brains: Path) -> BrainRegistry:
    try:
        return BrainLibrary(brains).load()
    except (ConfigError, ValueError) as error:
        console.print(f"[red]{error}[/red]")
        raise typer.Exit(2) from error


def _chosen_brain(registry: BrainRegistry, requested: str | None) -> str:
    try:
        return registry.resolve(requested)
    except ConfigError as error:
        console.print(f"[red]{error}[/red]  See [bold]lifeform brain[/bold].")
        raise typer.Exit(2) from error


def _resolve_worlds(library: PresetLibrary, worlds: list[str] | None) -> list[WorldPreset]:
    requested = worlds or [ALL_CORE_WORLDS]
    all_presets = library.load_all()
    if requested == [ALL_CORE_WORLDS]:
        return [preset for preset in all_presets if not preset.stretch]
    if requested == [ALL_WORLDS]:
        return all_presets
    try:
        return [library.load(slug) for slug in requested]
    except ConfigError as error:
        console.print(f"[red]{error}[/red]  Try [bold]lifeform worlds[/bold] to list them.")
        raise typer.Exit(2) from error


def _estimate(
    presets: list[WorldPreset], ticks: int | None, scale: float, settings: SystemOneSettings, tokens_per_call: int
) -> RunEstimate:
    return CostEstimator(settings, tokens_per_call).estimate(presets, ticks, scale)


def _describe_estimate(estimate: RunEstimate, settings: SystemOneSettings) -> None:
    console.print(estimate_table(estimate, settings.title))
    if settings.name == HEURISTIC_BRAIN:
        console.print(
            "[yellow]Brain: heuristic (offline development stand-in). No model calls and no cost; "
            "the run is stamped 'heuristic' and is neither a Jev nor a Kev result.[/yellow]"
        )
        return
    console.print(
        f"Brain: [bold]{settings.title}[/bold] ({settings.model} at {settings.base_url}).\n"
        f"{settings.title} will be called about [bold]{estimate.expected_calls:,}[/bold] times "
        f"(≈{estimate.expected_tokens / 1e6:,.1f}M input tokens at ≈{estimate.tokens_per_call:,} tokens per call).\n"
        f"Expected cost [bold green]${estimate.expected_usd:,.2f}[/bold green] "
        f"(ceiling [bold]${estimate.ceiling_usd:,.2f}[/bold] if every world reaches its population ceiling)."
    )
    if settings.host_usd_per_hour > 0.0:
        console.print(
            f"That includes hosting at ${settings.host_usd_per_hour:,.2f}/h: "
            f"≈[bold]${estimate.expected_hosting_usd:,.2f}[/bold] for the expected wall time."
        )
    elif settings.price_usd_per_million_input_tokens == 0.0:
        console.print(
            f"[yellow]{settings.title} has no per-token price here. If it runs on a rented GPU, set "
            f"host_usd_per_hour in brains.yaml so estimates and --max-usd include it.[/yellow]"
        )
    console.print(
        f"Expected wall time ≈ [bold]{_duration_text(estimate.expected_hours)}[/bold] at "
        f"{estimate.requests_per_minute:,.0f} requests/min (throughput, not cost, sets the pace)."
    )


def _duration_text(hours: float) -> str:
    if hours >= 1.0:
        return f"{hours:,.1f} h"
    return f"{max(1.0, hours * MINUTES_PER_HOUR):,.0f} min"


def _api_key(settings: SystemOneSettings) -> str:
    key = os.environ.get(settings.api_key_env, "").strip() if settings.api_key_env else ""
    if key:
        console.print(f"Using the {settings.title} API key from ${settings.api_key_env}.")
        return key
    if not settings.api_key_required:
        return UNAUTHENTICATED_KEY
    prompt = f"{settings.title} API key (input hidden, kept in memory only)"
    key = str(typer.prompt(prompt, hide_input=True)).strip()
    if not key:
        console.print(f"[red]An API key is required for {settings.title} runs.[/red]")
        raise typer.Exit(2)
    return key


def _system_one_brain(settings: SystemOneSettings, api_key: str) -> SystemOneBrain:
    governor = RateGovernor(settings.requests_per_minute, settings.tokens_per_second, settings.governor_start_fraction)
    return SystemOneBrain(settings, SystemOneGateway(settings, api_key, governor), PanelCodec())


def _decision_brain(settings: SystemOneSettings) -> Brain:
    if settings.name == HEURISTIC_BRAIN:
        return HeuristicBrain()
    return _system_one_brain(settings, _api_key(settings))


async def _preflight(settings: SystemOneSettings, api_key: str) -> tuple[dict[str, str], float]:
    governor = RateGovernor(settings.requests_per_minute, settings.tokens_per_second, settings.governor_start_fraction)
    gateway = SystemOneGateway(settings, api_key, governor)
    try:
        return await gateway.model_cards(), await gateway.probe_latency_ms()
    finally:
        await gateway.close()


def _print_setup_hint(settings: SystemOneSettings) -> None:
    if settings.setup_hint:
        console.print(f"[yellow]{settings.setup_hint}[/yellow]")


@app.command()
def worlds(presets: PresetsOption = Path("presets")) -> None:
    """List the available world settings."""
    console.print(world_table(_library(presets).load_all()))


@app.command()
def brain(
    name: Annotated[str | None, typer.Argument(help="Make this brain the default for future runs.")] = None,
    brains: BrainsOption = Path("brains.yaml"),
) -> None:
    """Show the available brains (Jev, Kev, heuristic), or switch the default with: lifeform brain kev."""
    registry = _registry(brains)
    if name is not None:
        _chosen_brain(registry, name)
        registry = BrainLibrary(brains).switch(name)
        console.print(f"Default brain is now [bold]{name}[/bold] (saved in {brains}).")
    console.print(brain_table(registry))
    console.print("Override it for a single command with [bold]--brain[/bold], for example: lifeform run --brain jev")


@app.command()
def estimate(
    worlds: WorldsArgument = None,
    ticks: TicksOption = None,
    population_scale: ScaleOption = 1.0,
    brain: BrainOption = None,
    tokens_per_call: Annotated[int, typer.Option(help="Assumed input tokens per call.")] = DEFAULT_TOKENS_PER_CALL,
    presets: PresetsOption = Path("presets"),
    brains: BrainsOption = Path("brains.yaml"),
) -> None:
    """Estimate calls, cost and wall time for a run without running it."""
    registry = _registry(brains)
    settings = registry.settings_for(_chosen_brain(registry, brain))
    chosen = _resolve_worlds(_library(presets), worlds)
    _describe_estimate(_estimate(chosen, ticks, population_scale, settings, tokens_per_call), settings)


@app.command()
def preflight(brain: BrainOption = None, brains: BrainsOption = Path("brains.yaml")) -> None:
    """Check the endpoint and API key, list its models and measure one call's latency."""
    registry = _registry(brains)
    chosen = _chosen_brain(registry, brain)
    if chosen == HEURISTIC_BRAIN:
        console.print("The heuristic stand-in runs offline and needs no preflight.")
        return
    settings = registry.provider(chosen)
    console.print(f"Checking [bold]{settings.title}[/bold] at {settings.base_url} …")
    try:
        cards, latency = asyncio.run(_preflight(settings, _api_key(settings)))
    except (BrainMisuse, BrainUnavailable) as error:
        console.print(f"[red]Preflight failed:[/red] {error}")
        _print_setup_hint(settings)
        raise typer.Exit(1) from error
    console.print(f"Models available: {', '.join(cards) or '(none listed)'}")
    pinned = settings.model in cards or any(settings.model.startswith(model) for model in cards)
    console.print(
        f"Pinned model {settings.model}: {'[green]available[/green]' if pinned else '[yellow]not listed[/yellow]'}"
    )
    if cards.get(settings.model):
        console.print(f"Served as: {cards[settings.model]}")
    console.print(f"One-call round trip: {latency:,.0f} ms")


@app.command()
def run(
    worlds: WorldsArgument = None,
    ticks: TicksOption = None,
    population_scale: ScaleOption = 1.0,
    seed: Annotated[int, typer.Option(help="Random seed.")] = 7,
    brain: BrainOption = None,
    max_usd: Annotated[float | None, typer.Option(help="Stop cleanly before spending more than this.")] = None,
    max_calls: Annotated[
        int | None, typer.Option(help="Stop cleanly before making more model calls than this.")
    ] = None,
    decision_detail: Annotated[str, typer.Option(help="Decision tape detail: full, summary or none.")] = "full",
    tokens_per_call: Annotated[
        int, typer.Option(help="Assumed input tokens per call for the estimate.")
    ] = DEFAULT_TOKENS_PER_CALL,
    label: Annotated[str, typer.Option(help="A short label stored with the run.")] = "",
    run_id: Annotated[str | None, typer.Option(help="Folder name under runs/ (default: a timestamp).")] = None,
    yes: Annotated[bool, typer.Option("--yes", "-y", help="Skip the cost confirmation.")] = False,
    presets: PresetsOption = Path("presets"),
    brains: BrainsOption = Path("brains.yaml"),
    output: Annotated[Path, typer.Option(help="Where run bundles are written.")] = Path("runs"),
) -> None:
    """Estimate the cost, ask for confirmation, then run the simulation and record it for replay."""
    detail = next((choice for choice in DECISION_DETAILS if choice == decision_detail), None)
    if detail is None:
        console.print("[red]--decision-detail must be full, summary or none.[/red]")
        raise typer.Exit(2)
    registry = _registry(brains)
    settings = registry.settings_for(_chosen_brain(registry, brain))
    chosen = _resolve_worlds(_library(presets), worlds)
    run_estimate = _estimate(chosen, ticks, population_scale, settings, tokens_per_call)
    _describe_estimate(run_estimate, settings)
    if max_usd is not None:
        console.print(f"Hard budget: the run stops cleanly before spending more than [bold]${max_usd:,.2f}[/bold].")
    if not yes and not typer.confirm("Proceed with this run?", default=False):
        console.print("Cancelled; nothing was spent.")
        raise typer.Exit(0)
    config = RunConfig(
        worlds=tuple(preset.slug for preset in chosen),
        ticks=ticks,
        seed=seed,
        population_scale=population_scale,
        brain=settings.name,
        system_one=settings,
        recording=RecordingSettings(decision_detail=detail),
        max_usd=max_usd,
        max_calls=max_calls,
        output_directory=output,
        presets_directory=presets,
        run_id=run_id,
        label=label,
    )
    outcome = asyncio.run(_run(config, _decision_brain(settings), run_estimate))
    console.print(outcome_table(outcome))
    console.print(
        f"Spent ≈ [bold]${outcome.spent_usd:,.4f}[/bold] on {outcome.calls:,} calls "
        f"({outcome.tokens:,} input tokens). Bundle: [bold]{outcome.directory}[/bold]"
    )
    console.print("Replay it with [bold]lifeform serve[/bold] and open the printed address.")


async def _with_served_model(config: RunConfig, brain: Brain) -> RunConfig:
    if not isinstance(brain, SystemOneBrain):
        return config
    served = await brain.served_model()
    console.print(f"{brain.settings.title} is serving: {served}")
    return config.model_copy(update={"notes": {**config.notes, SERVED_MODEL_NOTE: served}})


async def _run(config: RunConfig, brain: Brain, run_estimate: RunEstimate) -> RunOutcome:
    title = config.system_one.title
    try:
        described = await _with_served_model(config, brain)
        with ConsoleReporter(console) as reporter:
            return await RunOrchestrator(described, brain, reporter, run_estimate).run()
    except BrainUnavailable as error:
        console.print(f"[red]{title} is not reachable:[/red] {error}")
        _print_setup_hint(config.system_one)
        raise typer.Exit(1) from error
    except BrainMisuse as error:
        console.print(f"[red]{title} rejected the request:[/red] {error}")
        raise typer.Exit(1) from error
    finally:
        await brain.close()


@app.command()
def runs(output: Annotated[Path, typer.Option(help="Where run bundles live.")] = Path("runs")) -> None:
    """List recorded runs."""
    for manifest in sorted(output.glob("*/run.json")):
        data = json.loads(manifest.read_text(encoding="utf-8"))
        worlds_text = ", ".join(f"{world['slug']}({world.get('status')})" for world in data.get("worlds", []))
        console.print(
            f"[bold]{data['run_id']}[/bold]  brain={data['brain']}  ${data['totals']['usd']:,.4f}  {worlds_text}"
        )


@app.command()
def serve(
    host: Annotated[str, typer.Option()] = "127.0.0.1",
    port: Annotated[int, typer.Option()] = 8765,
    output: Annotated[Path, typer.Option(help="Where run bundles live.")] = Path("runs"),
    web: Annotated[Path, typer.Option(help="Built web theater directory.")] = Path("web/dist"),
    presets: PresetsOption = Path("presets"),
    archetypes: Annotated[Path, typer.Option(help="Directory of species archetypes.")] = Path("archetypes"),
    brains: BrainsOption = Path("brains.yaml"),
) -> None:
    """Serve recorded runs and the replay theater."""
    console.print(f"Replay theater at [bold]http://{host}:{port}[/bold]  (runs from {output})")
    uvicorn.run(create_app(output, web, presets, archetypes, brains), host=host, port=port, log_level="warning")


def main() -> None:
    app()
