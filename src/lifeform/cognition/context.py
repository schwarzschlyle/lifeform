from __future__ import annotations

import dataclasses
from collections.abc import Callable
from dataclasses import dataclass

from lifeform.biology.drives import Condition, DriveState
from lifeform.biology.organism import Organism
from lifeform.perception.percepts import PerceptualField
from lifeform.world.entities import Carcass
from lifeform.world.world import World


@dataclass(slots=True)
class MindContext:
    organism: Organism
    world: World
    field: PerceptualField
    drives: DriveState
    conditions: Condition
    tick: int
    season_index: int
    animals: Callable[[int], Organism | None]
    carcasses: Callable[[int], Carcass | None]
    noticed: Callable[[int, int], bool]
    species_name: Callable[[int], str]
    mate_eligible: Callable[[Organism], bool]
    group: list[Organism] = dataclasses.field(default_factory=list)
    last_outcome: str | None = None
