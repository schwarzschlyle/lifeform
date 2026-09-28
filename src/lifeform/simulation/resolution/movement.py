from __future__ import annotations

import heapq
import math
from collections.abc import Callable
from dataclasses import dataclass, field
from enum import StrEnum

import numpy as np

from lifeform.biology.organism import Organism
from lifeform.core.geometry import Direction, Position
from lifeform.simulation.population import Population
from lifeform.world.terrain import IMPASSABLE
from lifeform.world.world import World

REFERENCE_OCCUPANT_KG = 20.0
MIN_OCCUPANCY = 0.1
PATCH_CAPACITY = 1.0
TERRAIN_COST_WEIGHT = 0.1
COVER_PREFERENCE = 0.5
MAX_SEARCH_EXPANSIONS = 600
DIAGONAL_COST = math.sqrt(2.0)


class MoveMode(StrEnum):
    TOWARD = "toward"
    AWAY = "away"
    DIRECTION = "direction"
    DESTINATION = "destination"


@dataclass(slots=True)
class MoverPlan:
    organism: Organism
    steps: int
    mode: MoveMode
    effort: int
    target_id: int | None = None
    point: Position | None = None
    direction: Direction | None = None
    stop_distance: float = 0.0
    taken: int = 0
    finished: bool = False


@dataclass(slots=True)
class MovementReport:
    paths: dict[int, list[Position]] = field(default_factory=dict)
    locomotion_units: dict[int, float] = field(default_factory=dict)
    ambush_triggers: list[tuple[int, int]] = field(default_factory=list)


class OccupancyLedger:
    def __init__(self, population: Population) -> None:
        self._load: dict[Position, float] = {}
        for organism in population.living():
            self._add(organism.position, self.units(organism))

    @staticmethod
    def units(organism: Organism) -> float:
        if not organism.reproduction.weaned:
            return 0.0
        return min(1.0, max(MIN_OCCUPANCY, organism.body.mass_kg / REFERENCE_OCCUPANT_KG))

    def can_enter(self, organism: Organism, position: Position) -> bool:
        return self._load.get(position, 0.0) + self.units(organism) <= PATCH_CAPACITY + 1e-9

    def move(self, organism: Organism, origin: Position, destination: Position) -> None:
        units = self.units(organism)
        self._add(origin, -units)
        self._add(destination, units)

    def _add(self, position: Position, units: float) -> None:
        self._load[position] = self._load.get(position, 0.0) + units


class LocalPlanner:
    def __init__(self, world: World, ledger: OccupancyLedger) -> None:
        self._world = world
        self._ledger = ledger

    def toward(self, organism: Organism, goal: Position) -> Position | None:
        greedy = self._greedy(organism, goal, away=False)
        return greedy if greedy is not None else self._searched_step(organism, goal)

    def away(self, organism: Organism, threat: Position) -> Position | None:
        return self._greedy(organism, threat, away=True)

    def along(self, organism: Organism, direction: Direction) -> Position | None:
        for heading in (direction, Direction((direction + 1) % 8), Direction((direction - 1) % 8)):
            step = self._world.metric.step(organism.position, heading)
            if self._enterable(organism, step):
                return step
        return None

    def _greedy(self, organism: Organism, goal: Position, away: bool) -> Position | None:
        metric = self._world.metric
        current = metric.distance(organism.position, goal)
        best: Position | None = None
        best_score = math.inf
        for direction in Direction:
            step = metric.step(organism.position, direction)
            if not self._enterable(organism, step):
                continue
            distance = metric.distance(step, goal)
            cost = self._world.move_cost(step, organism.trait("swim_skill"))
            if away:
                if distance < current:
                    continue
                score = -distance + TERRAIN_COST_WEIGHT * cost - COVER_PREFERENCE * self._world.cover(step)
            else:
                if distance >= current:
                    continue
                score = distance + TERRAIN_COST_WEIGHT * cost
            if score < best_score:
                best, best_score = step, score
        return best

    def _searched_step(self, organism: Organism, goal: Position) -> Position | None:
        metric = self._world.metric
        start = organism.position
        frontier: list[tuple[float, int, Position]] = [(0.0, 0, start)]
        came_from: dict[Position, Position] = {}
        spent: dict[Position, float] = {start: 0.0}
        counter = 0
        while frontier and counter < MAX_SEARCH_EXPANSIONS:
            _, _, current = heapq.heappop(frontier)
            if metric.are_adjacent(current, goal) or current == goal:
                return self._first_step(organism, came_from, start, current)
            for direction in Direction:
                step = metric.step(current, direction)
                cost = self._world.move_cost(step, organism.trait("swim_skill"))
                if cost == IMPASSABLE:
                    continue
                total = spent[current] + cost * (DIAGONAL_COST if direction.is_diagonal else 1.0)
                if total < spent.get(step, math.inf):
                    spent[step] = total
                    came_from[step] = current
                    counter += 1
                    heapq.heappush(frontier, (total + metric.distance(step, goal), counter, step))
        return None

    def _first_step(
        self, organism: Organism, came_from: dict[Position, Position], start: Position, end: Position
    ) -> Position | None:
        node = end
        while came_from.get(node) is not None and came_from[node] != start:
            node = came_from[node]
        if node == start:
            return None
        return node if self._enterable(organism, node) else None

    def _enterable(self, organism: Organism, position: Position) -> bool:
        passable = self._world.is_passable(position, organism.trait("swim_skill"))
        return passable and self._ledger.can_enter(organism, position)


class SubStepMover:
    def __init__(self, world: World, population: Population, rng: np.random.Generator) -> None:
        self._world = world
        self._population = population
        self._rng = rng

    def run(
        self, plans: list[MoverPlan], ambushers: list[Organism], ambush_suitable: Callable[[Organism, Organism], bool]
    ) -> MovementReport:
        report = MovementReport()
        ledger = OccupancyLedger(self._population)
        planner = LocalPlanner(self._world, ledger)
        order = self._initiative(plans)
        triggered: set[int] = set()
        for _ in range(max((plan.steps for plan in plans), default=0)):
            for plan in order:
                if plan.finished or plan.taken >= plan.steps:
                    continue
                self._advance(plan, planner, ledger, report)
                self._check_ambushes(plan.organism, ambushers, ambush_suitable, triggered, report)
        return report

    def _initiative(self, plans: list[MoverPlan]) -> list[MoverPlan]:
        tiebreak = self._rng.random(len(plans))
        ranked = sorted(zip(plans, tiebreak, strict=True), key=_initiative_key)
        return [plan for plan, _ in ranked]

    def _advance(self, plan: MoverPlan, planner: LocalPlanner, ledger: OccupancyLedger, report: MovementReport) -> None:
        organism = plan.organism
        goal = self._goal(plan)
        if goal is None and plan.mode != MoveMode.DIRECTION:
            plan.finished = True
            return
        metric = self._world.metric
        if (
            goal is not None
            and plan.mode != MoveMode.AWAY
            and metric.distance(organism.position, goal) <= (plan.stop_distance)
        ):
            plan.finished = True
            return
        step = self._next_step(plan, planner, goal)
        if step is None:
            plan.finished = True
            return
        origin = organism.position
        ledger.move(organism, origin, step)
        direction = metric.direction(origin, step)
        organism.body.position = step
        organism.body.heading = direction
        cost = self._world.move_cost(step, organism.trait("swim_skill"))
        report.paths.setdefault(organism.id, []).append(step)
        report.locomotion_units[organism.id] = report.locomotion_units.get(organism.id, 0.0) + cost * (
            DIAGONAL_COST if direction.is_diagonal else 1.0
        )
        plan.taken += 1

    def _goal(self, plan: MoverPlan) -> Position | None:
        if plan.mode in (MoveMode.TOWARD, MoveMode.AWAY):
            target = self._population.get(plan.target_id)
            if target is not None and target.alive:
                return target.position
            return plan.point
        return plan.point

    def _next_step(self, plan: MoverPlan, planner: LocalPlanner, goal: Position | None) -> Position | None:
        organism = plan.organism
        if plan.mode == MoveMode.DIRECTION:
            return planner.along(organism, plan.direction) if plan.direction is not None else None
        if goal is None:
            return None
        if plan.mode == MoveMode.AWAY:
            return planner.away(organism, goal)
        return planner.toward(organism, goal)

    def _check_ambushes(
        self,
        mover: Organism,
        ambushers: list[Organism],
        ambush_suitable: Callable[[Organism, Organism], bool],
        triggered: set[int],
        report: MovementReport,
    ) -> None:
        for ambusher in ambushers:
            if ambusher.id in triggered or ambusher.id == mover.id:
                continue
            if self._world.metric.are_adjacent(ambusher.position, mover.position) and ambush_suitable(ambusher, mover):
                triggered.add(ambusher.id)
                report.ambush_triggers.append((ambusher.id, mover.id))


def _initiative_key(entry: tuple[MoverPlan, float]) -> tuple[int, float, float]:
    plan, tiebreak = entry
    return -plan.effort, -plan.organism.trait("limb_ratio"), float(tiebreak)
