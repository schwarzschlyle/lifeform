from __future__ import annotations

from dataclasses import dataclass, field

from lifeform.biology.drives import Condition, DriveState
from lifeform.biology.physiology import ActivityRecord
from lifeform.cognition.decision import Intent, RawDecision
from lifeform.cognition.mind_state import MindState
from lifeform.cognition.question_panel import QuestionPanel
from lifeform.core.events import DomainEvent, EventBus, EventKind
from lifeform.core.geometry import Position
from lifeform.perception.percepts import PerceptualField
from lifeform.simulation.population import Population
from lifeform.simulation.services import Ecosystem
from lifeform.world.world import World


@dataclass(slots=True)
class OrganismTickRecord:
    activity: ActivityRecord = field(default_factory=ActivityRecord)
    path: list[Position] = field(default_factory=list)
    outcome: str | None = None
    basking: bool = False
    shaded: bool = False
    in_water: bool = False
    huddling: bool = False
    ate_kg: float = 0.0
    ate_meat_of: int | None = None
    drank_litres: float = 0.0
    struck: list[int] = field(default_factory=list)
    struck_by: list[int] = field(default_factory=list)
    mated_with: int | None = None
    groomed_by: list[int] = field(default_factory=list)
    threatened_by: int | None = None


@dataclass(slots=True)
class PersistentState:
    moved_fast: set[int] = field(default_factory=set)
    last_outcomes: dict[int, str] = field(default_factory=dict)
    last_intents: dict[int, Intent] = field(default_factory=dict)
    threatened_by: dict[int, int] = field(default_factory=dict)


@dataclass(slots=True)
class TickContext:
    tick: int
    world: World
    population: Population
    services: Ecosystem
    bus: EventBus
    persistent: PersistentState
    drives: dict[int, DriveState] = field(default_factory=dict)
    conditions: dict[int, Condition] = field(default_factory=dict)
    fields: dict[int, PerceptualField] = field(default_factory=dict)
    minds: dict[int, MindState] = field(default_factory=dict)
    panels: dict[int, QuestionPanel] = field(default_factory=dict)
    decisions: dict[int, RawDecision] = field(default_factory=dict)
    intents: dict[int, Intent] = field(default_factory=dict)
    records: dict[int, OrganismTickRecord] = field(default_factory=dict)
    born: list[int] = field(default_factory=list)
    died: list[int] = field(default_factory=list)
    events: list[DomainEvent] = field(default_factory=list)

    def record(self, organism_id: int) -> OrganismTickRecord:
        if organism_id not in self.records:
            self.records[organism_id] = OrganismTickRecord()
        return self.records[organism_id]

    def emit(
        self, kind: EventKind, actors: tuple[int, ...] = (), position: Position | None = None, **payload: object
    ) -> None:
        event = DomainEvent(self.tick, kind, actors, (position.x, position.y) if position else None, dict(payload))
        self.events.append(event)
        self.bus.publish(event)

    def perceived(self, observer_id: int, target_id: int) -> bool:
        field_of_observer = self.fields.get(observer_id)
        return field_of_observer is not None and target_id in field_of_observer.animal_ids()
