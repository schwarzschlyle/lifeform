from __future__ import annotations

import math
from collections.abc import Callable, Iterable

import numpy as np

from lifeform.biology.mechanics import BodyMechanics
from lifeform.biology.organism import Organism
from lifeform.config.parameters import PerceptionParameters
from lifeform.core.geometry import Direction, Position
from lifeform.perception.percepts import EntityKind, EntityPercept, ScentPercept, SoundPercept
from lifeform.world.acoustics import received_level_db
from lifeform.world.entities import Carcass
from lifeform.world.fields import ScentLandscape
from lifeform.world.world import World

REFERENCE_MASS_KG = 20.0
APPARENT_SIZE_EXPONENT = 2.0 / 3.0
IDENTIFICATION_DIFFICULTY = 3.0
MIN_TRANSMITTANCE = 0.05
ACUITY_FLOOR = 0.3
CARCASS_CERTAINTY_BONUS = 0.2
WIND_UPWIND_DOT = 0.3
BLOCKING_OPACITY = 0.5
TOUCH_DISTANCE = 1.5
MIN_EFFECTIVE_LIGHT = 0.02
MIN_CARCASS_LIGHT = 0.05
CRYPSIS_BASE = 0.5
HIDDEN_COVER_EFFECT = 0.8


def line_of_sight_transmittance(world: World, origin: Position, target: Position, viewer_elevation_m: float) -> float:
    dx, dy = world.metric.delta(origin, target)
    steps = max(abs(dx), abs(dy))
    transmittance = 1.0
    for step in range(1, steps):
        position = world.metric.wrap(origin.x + round(dx * step / steps), origin.y + round(dy * step / steps))
        opacity = world.sight_opacity(position)
        if opacity >= BLOCKING_OPACITY and float(world.elevation_m[position.y, position.x]) > viewer_elevation_m:
            return 0.0
        transmittance *= 1.0 - opacity
        if transmittance < MIN_TRANSMITTANCE:
            return 0.0
    return transmittance


class VisionSense:
    def __init__(self, parameters: PerceptionParameters, mechanics: BodyMechanics, rng: np.random.Generator) -> None:
        self._parameters = parameters
        self._mechanics = mechanics
        self._rng = rng

    def perceive_animals(
        self, viewer: Organism, world: World, candidates: Iterable[Organism], moved_recently: Callable[[int], bool]
    ) -> list[EntityPercept]:
        light = world.light(viewer.position)
        radius = self._mechanics.vision_radius(viewer, light)
        viewer_elevation = float(world.elevation_m[viewer.position.y, viewer.position.x])
        percepts: list[EntityPercept] = []
        for target in candidates:
            if target.id == viewer.id or not target.alive:
                continue
            distance = world.metric.distance(viewer.position, target.position)
            touching = distance < TOUCH_DISTANCE
            if touching:
                percepts.append(self._touch(viewer, world, target, distance))
                continue
            if distance > radius or target.body.in_den:
                continue
            moving = moved_recently(target.id)
            signal = self._signal(viewer, world, target.body.mass_kg, target, light, moving) * (
                line_of_sight_transmittance(world, viewer.position, target.position, viewer_elevation)
            )
            percept = self._detected(viewer, world, target.id, target.position, distance, signal, moving)
            if percept is not None:
                percepts.append(percept)
        return percepts

    def perceive_carcasses(self, viewer: Organism, world: World, carcasses: Iterable[Carcass]) -> list[EntityPercept]:
        light = world.light(viewer.position)
        radius = self._mechanics.vision_radius(viewer, light)
        percepts: list[EntityPercept] = []
        for carcass in carcasses:
            distance = world.metric.distance(viewer.position, carcass.position)
            if distance > max(radius, TOUCH_DISTANCE):
                continue
            size = math.pow(carcass.mass_kg / REFERENCE_MASS_KG, APPARENT_SIZE_EXPONENT)
            signal = (ACUITY_FLOOR + viewer.trait("visual_acuity")) * max(light, MIN_CARCASS_LIGHT) * size
            certainty = min(1.0, self._certainty(signal, distance) + CARCASS_CERTAINTY_BONUS)
            direction = world.metric.direction(viewer.position, carcass.position)
            percepts.append(
                EntityPercept(
                    EntityKind.CARCASS,
                    carcass.carcass_id,
                    carcass.position,
                    distance,
                    direction,
                    certainty,
                    distance < TOUCH_DISTANCE,
                    False,
                )
            )
        return percepts

    def _touch(self, viewer: Organism, world: World, target: Organism, distance: float) -> EntityPercept:
        direction = world.metric.direction(viewer.position, target.position)
        return EntityPercept(EntityKind.ANIMAL, target.id, target.position, distance, direction, 1.0, True, False)

    def _signal(
        self, viewer: Organism, world: World, mass_kg: float, target: Organism, light: float, moving: bool
    ) -> float:
        parameters = self._parameters
        effective_light = light + parameters.night_vision_compensation * viewer.trait("night_vision") * (1 - light)
        size = math.pow(mass_kg / REFERENCE_MASS_KG, APPARENT_SIZE_EXPONENT)
        concealment = (
            parameters.crypsis_strength
            * world.cover(target.position)
            * (CRYPSIS_BASE + (1.0 - CRYPSIS_BASE) * target.trait("crypsis"))
        )
        if target.body.hidden:
            concealment = max(concealment, HIDDEN_COVER_EFFECT * world.cover(target.position))
        still = target.body.frozen or target.body.stalking or target.body.ambushing or target.body.hidden
        motion = parameters.moving_detectability if moving else (parameters.still_detectability if still else 1.0)
        display = 1.0 + parameters.ornament_detectability * target.trait("ornament")
        acuity = ACUITY_FLOOR + viewer.trait("visual_acuity")
        return acuity * max(effective_light, MIN_EFFECTIVE_LIGHT) * size * (1.0 - concealment) * motion * display

    def _detected(
        self,
        viewer: Organism,
        world: World,
        target_id: int,
        position: Position,
        distance: float,
        signal: float,
        moving: bool,
    ) -> EntityPercept | None:
        probability = 1.0 - math.exp(-self._parameters.detection_kappa * signal / max(distance, 1.0) ** 2)
        if self._rng.random() >= probability:
            return None
        certainty = min(1.0, self._certainty(signal, distance) + viewer.body.certainty_bonus)
        direction = world.metric.direction(viewer.position, position)
        return EntityPercept(EntityKind.ANIMAL, target_id, position, distance, direction, certainty, False, moving)

    def _certainty(self, signal: float, distance: float) -> float:
        kappa = self._parameters.detection_kappa / IDENTIFICATION_DIFFICULTY
        return 1.0 - math.exp(-kappa * signal / max(distance, 1.0) ** 2)


class OlfactionSense:
    def __init__(self, mechanics: BodyMechanics) -> None:
        self._mechanics = mechanics

    def perceive(self, smeller: Organism, world: World, kind_nearby: bool) -> list[ScentPercept]:
        threshold = self._mechanics.smell_threshold(smeller)
        position = smeller.position
        wind = world.climate_state.wind
        percepts: list[ScentPercept] = []
        for channel, grid in world.fields.scent.channels.items():
            if not self._meaningful(smeller, channel):
                continue
            here = float(grid[position.y, position.x])
            strongest_direction, strongest = self._strongest_neighbor(world, grid, position)
            peak = max(here, strongest)
            if peak <= threshold:
                continue
            direction = strongest_direction if strongest > here else None
            own_trail = channel == ScentLandscape.musk_name(smeller.species_id) and direction is None
            if own_trail and not kind_nearby:
                continue
            percepts.append(
                ScentPercept(
                    channel, peak / threshold, direction, self._upwind(direction, wind), self._species(channel)
                )
            )
        return percepts

    @staticmethod
    def _strongest_neighbor(world: World, grid: np.ndarray, position: Position) -> tuple[Direction, float]:
        best_direction = Direction.NORTH
        best_value = -1.0
        for direction in Direction:
            step = world.metric.step(position, direction)
            value = float(grid[step.y, step.x])
            if value > best_value:
                best_direction, best_value = direction, value
        return best_direction, best_value

    @staticmethod
    def _upwind(direction: Direction | None, wind: tuple[float, float]) -> bool:
        if direction is None:
            return False
        dx, dy = direction.offset
        speed = math.hypot(*wind)
        if speed < 1e-6:
            return False
        return -(dx * wind[0] + dy * wind[1]) / (math.hypot(dx, dy) * speed) > WIND_UPWIND_DOT

    @staticmethod
    def _meaningful(smeller: Organism, channel: str) -> bool:
        if not channel.startswith(ScentLandscape.ESTRUS_PREFIX):
            return True
        same_kind = ScentLandscape.species_of(channel) == smeller.species_id
        return same_kind and not smeller.reproduction.is_female and smeller.is_adult

    @staticmethod
    def _species(channel: str) -> int | None:
        return ScentLandscape.species_of(channel)


class HearingSense:
    def __init__(self, parameters: PerceptionParameters, mechanics: BodyMechanics, rng: np.random.Generator) -> None:
        self._parameters = parameters
        self._mechanics = mechanics
        self._rng = rng

    def perceive(self, listener: Organism, world: World) -> list[SoundPercept]:
        threshold = self._mechanics.hearing_threshold_db(listener)
        if world.climate_state.storm:
            threshold += self._parameters.storm_masking_db
        percepts: list[SoundPercept] = []
        for event in world.sounds.audible:
            if event.source_id == listener.id:
                continue
            distance = world.metric.distance(listener.position, event.position)
            level = received_level_db(event.level_db, distance, self._parameters.hearing_attenuation_per_patch_db)
            if level <= threshold:
                continue
            direction = world.metric.direction(listener.position, event.position)
            if self._rng.random() > listener.trait("hearing"):
                direction = Direction((direction + int(self._rng.choice((-1, 1)))) % 8)
            percepts.append(SoundPercept(event, level - threshold, direction, distance))
        return percepts
