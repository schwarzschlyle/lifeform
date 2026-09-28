from __future__ import annotations

import asyncio
import time
from collections.abc import Callable
from dataclasses import dataclass
from functools import partial

from lifeform.biology.organism import Organism
from lifeform.cognition.brain import Brain, BrainUnavailable
from lifeform.cognition.context import MindContext
from lifeform.cognition.decision import RawDecision
from lifeform.simulation.context import TickContext

RETRY_INITIAL_SECONDS = 1.0
RETRY_MAX_SECONDS = 60.0

ProgressCallback = Callable[[int, int], None]


class DeliberationStalled(RuntimeError):
    """Jev stayed unreachable past the configured patience; the run should checkpoint and pause."""


@dataclass(frozen=True, slots=True)
class DeliberationOptions:
    patience_seconds: float = 600.0
    allow_stalls: bool = False


class DeliberationPhase:
    name = "deliberation"

    def __init__(self, brain: Brain, options: DeliberationOptions, progress: ProgressCallback | None = None) -> None:
        self._brain = brain
        self._options = options
        self._progress = progress

    async def run(self, context: TickContext) -> None:
        organisms = context.population.living()
        for organism in organisms:
            self._prepare(context, organism)
        pending = [organism.id for organism in organisms]
        completed = 0
        started = time.monotonic()
        delay = RETRY_INITIAL_SECONDS
        while pending:
            results = await asyncio.gather(
                *(self._decide(context, organism_id) for organism_id in pending), return_exceptions=True
            )
            still_pending: list[int] = []
            for organism_id, result in zip(pending, results, strict=True):
                if isinstance(result, BrainUnavailable):
                    still_pending.append(organism_id)
                elif isinstance(result, BaseException):
                    raise result
                else:
                    context.decisions[organism_id] = result
                    completed += 1
                    if self._progress is not None:
                        self._progress(completed, len(organisms))
            pending = still_pending
            if pending:
                if time.monotonic() - started > self._options.patience_seconds:
                    if self._options.allow_stalls:
                        return
                    raise DeliberationStalled(
                        f"{len(pending)} decisions still unanswered after {self._options.patience_seconds:.0f}s"
                    )
                await asyncio.sleep(delay)
                delay = min(RETRY_MAX_SECONDS, delay * 2.0)

    async def _decide(self, context: TickContext, organism_id: int) -> RawDecision:
        return await self._brain.decide(context.minds[organism_id], context.panels[organism_id])

    def _prepare(self, context: TickContext, organism: Organism) -> None:
        services = context.services
        mind_context = self._mind_context(context, organism)
        menu = services.affordances.generate(mind_context)
        mind = services.encoder.encode(mind_context)
        context.minds[organism.id] = mind
        context.panels[organism.id] = services.panels.build(organism, menu, mind.focus_options)

    @staticmethod
    def _mind_context(context: TickContext, organism: Organism) -> MindContext:
        services = context.services
        world = context.world
        season = world.calendar.season_index(context.tick)
        radius = services.ecology.social.group_radius_patches
        group = [
            other
            for other in context.population.within(organism.position, radius)
            if other.species_id == organism.species_id and other.id != organism.id
        ]
        return MindContext(
            organism=organism,
            world=world,
            field=context.fields[organism.id],
            drives=context.drives[organism.id],
            conditions=context.conditions[organism.id],
            tick=context.tick,
            season_index=season,
            animals=context.population.any,
            carcasses=world.carcasses.items.get,
            noticed=context.perceived,
            species_name=services.species.name_of,
            mate_eligible=partial(services.clock.eligible, season_index=season),
            group=group,
            last_outcome=context.persistent.last_outcomes.get(organism.id),
        )
