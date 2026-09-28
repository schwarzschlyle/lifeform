from __future__ import annotations

from typing import Protocol

from lifeform.cognition.brain import Brain
from lifeform.core.events import EventBus
from lifeform.simulation.context import PersistentState, TickContext
from lifeform.simulation.disturbances import DisturbanceDirector
from lifeform.simulation.phases.action import ActionPhase
from lifeform.simulation.phases.deliberation import DeliberationOptions, DeliberationPhase, ProgressCallback
from lifeform.simulation.phases.environment import EnvironmentPhase
from lifeform.simulation.phases.evolution import EvolutionPhase
from lifeform.simulation.phases.intent import IntentPhase
from lifeform.simulation.phases.learning import LearningPhase
from lifeform.simulation.phases.lifecycle import LifecyclePhase
from lifeform.simulation.phases.perception import PerceptionPhase
from lifeform.simulation.phases.physiology import PhysiologyPhase
from lifeform.simulation.world_factory import BuiltWorld

PHASE_ORDER: tuple[str, ...] = (
    "environment",
    "perception",
    "deliberation",
    "intent",
    "action",
    "physiology",
    "learning",
    "lifecycle",
    "evolution",
    "recording",
)


class Phase(Protocol):
    name: str

    def run(self, context: TickContext) -> None: ...


class TickObserver(Protocol):
    def on_tick(self, context: TickContext) -> None: ...


class Simulation:
    def __init__(
        self, built: BuiltWorld, brain: Brain, options: DeliberationOptions, progress: ProgressCallback | None = None
    ) -> None:
        self.world = built.world
        self.population = built.population
        self.services = built.services
        self.bus = EventBus()
        self.persistent = PersistentState()
        self.observers: list[TickObserver] = []
        self.tick = 0
        disturbances = DisturbanceDirector(self.world.preset.disturbances, self.services.streams.stream("disturbances"))
        self._before: list[Phase] = [EnvironmentPhase(disturbances), PerceptionPhase()]
        self._deliberation = DeliberationPhase(brain, options, progress)
        self._after: list[Phase] = [
            IntentPhase(),
            ActionPhase(),
            PhysiologyPhase(disturbances),
            LearningPhase(),
            LifecyclePhase(),
            EvolutionPhase(),
        ]

    def observe(self, observer: TickObserver) -> None:
        self.observers.append(observer)

    async def advance(self) -> TickContext:
        self.tick += 1
        self.population.forget_deceased()
        context = TickContext(self.tick, self.world, self.population, self.services, self.bus, self.persistent)
        for phase in self._before:
            phase.run(context)
        await self._deliberation.run(context)
        for phase in self._after:
            phase.run(context)
        for observer in self.observers:
            observer.on_tick(context)
        return context
