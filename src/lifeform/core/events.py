from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any


class EventKind(StrEnum):
    BIRTH = "birth"
    DEATH = "death"
    STRIKE = "strike"
    MATING = "mating"
    CONCEPTION = "conception"
    MISCARRIAGE = "miscarriage"
    WEANING = "weaning"
    MATURITY = "maturity"
    CONTEST = "contest"
    SPECIATION = "speciation"
    EXTINCTION = "extinction"
    INFECTION = "infection"
    OUTBREAK = "outbreak"
    FIRE_START = "fire_start"
    ERUPTION = "eruption"
    RIFT_OPEN = "rift_open"
    DROUGHT_START = "drought_start"
    RAFTING = "rafting"
    DEN_BUILT = "den_built"
    CALL = "call"


@dataclass(frozen=True, slots=True)
class DomainEvent:
    tick: int
    kind: EventKind
    actors: tuple[int, ...] = ()
    position: tuple[int, int] | None = None
    payload: dict[str, Any] = field(default_factory=dict)


EventHandler = Callable[[DomainEvent], None]


class EventBus:
    def __init__(self) -> None:
        self._handlers: list[EventHandler] = []

    def subscribe(self, handler: EventHandler) -> None:
        self._handlers.append(handler)

    def publish(self, event: DomainEvent) -> None:
        for handler in self._handlers:
            handler(event)
