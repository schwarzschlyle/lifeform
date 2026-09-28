from __future__ import annotations

import math
from collections import deque
from dataclasses import dataclass, field
from functools import partial
from operator import attrgetter

from lifeform.core.geometry import Position, TorusMetric

MERGE_RADIUS_PATCHES = 3.0
INHERITED_CONFIDENCE = 0.5


@dataclass(slots=True)
class PlaceMemory:
    kind: str
    position: Position
    quality: float
    tick_seen: int
    base_confidence: float = 1.0

    def confidence(self, tick: int, half_life_ticks: float) -> float:
        return self.base_confidence * math.exp(-math.log(2.0) * (tick - self.tick_seen) / half_life_ticks)

    def value(self, tick: int, half_life_ticks: float) -> float:
        return self.quality * self.confidence(tick, half_life_ticks)


@dataclass(slots=True)
class AcquaintanceMemory:
    organism_id: int
    species_id: int
    relation: str
    valence: float
    tick_seen: int

    @property
    def eviction_rank(self) -> tuple[float, int]:
        return abs(self.valence), self.tick_seen


@dataclass(frozen=True, slots=True)
class Episode:
    tick: int
    text: str


class SpatialMemory:
    def __init__(self, slots: int, half_life_ticks: float, metric: TorusMetric) -> None:
        self.slots = slots
        self.half_life_ticks = half_life_ticks
        self._metric = metric
        self.places: list[PlaceMemory] = []

    def remember(self, kind: str, position: Position, quality: float, tick: int, base_confidence: float = 1.0) -> None:
        for place in self.places:
            if place.kind == kind and self._metric.distance(place.position, position) <= MERGE_RADIUS_PATCHES:
                place.position = position
                place.quality = quality
                place.tick_seen = tick
                place.base_confidence = max(place.base_confidence, base_confidence)
                return
        self.places.append(PlaceMemory(kind, position, quality, tick, base_confidence))
        if len(self.places) > self.slots:
            self.places.remove(min(self.places, key=self._ranking(tick)))

    def forget(self, kind: str, position: Position) -> None:
        self.places = [
            place
            for place in self.places
            if not (place.kind == kind and self._metric.distance(place.position, position) <= MERGE_RADIUS_PATCHES)
        ]

    def recall(self, kind_prefix: str, tick: int) -> list[PlaceMemory]:
        matching = [place for place in self.places if place.kind.startswith(kind_prefix)]
        return sorted(matching, key=self._ranking(tick), reverse=True)

    def strongest(self, count: int, tick: int) -> list[PlaceMemory]:
        return sorted(self.places, key=self._ranking(tick), reverse=True)[:count]

    def _ranking(self, tick: int) -> partial[float]:
        return partial(PlaceMemory.value, tick=tick, half_life_ticks=self.half_life_ticks)


class SocialMemory:
    def __init__(self, slots: int) -> None:
        self.slots = slots
        self.known: dict[int, AcquaintanceMemory] = {}

    def note(self, organism_id: int, species_id: int, relation: str, valence: float, tick: int) -> None:
        existing = self.known.get(organism_id)
        if existing is not None:
            existing.relation = relation if relation != "acquaintance" else existing.relation
            existing.valence = 0.7 * existing.valence + 0.3 * valence
            existing.tick_seen = tick
            return
        self.known[organism_id] = AcquaintanceMemory(organism_id, species_id, relation, valence, tick)
        if len(self.known) > self.slots:
            evicted = min(self.known.values(), key=attrgetter("eviction_rank"))
            del self.known[evicted.organism_id]

    def relation_to(self, organism_id: int) -> AcquaintanceMemory | None:
        return self.known.get(organism_id)


class EpisodicMemory:
    def __init__(self, slots: int) -> None:
        self.episodes: deque[Episode] = deque(maxlen=slots)

    def record(self, tick: int, text: str) -> None:
        self.episodes.append(Episode(tick, text))


@dataclass(slots=True)
class AssociativeLearner:
    learning_rate: float
    habituation_rate: float
    values: dict[str, float] = field(default_factory=dict)
    exposures: dict[str, int] = field(default_factory=dict)

    def learn(self, stimulus: str, outcome: float, salience: float = 1.0) -> None:
        current = self.values.get(stimulus, 0.0)
        alpha = min(1.0, self.learning_rate * salience)
        self.values[stimulus] = current + alpha * (outcome - current)

    def expose(self, stimulus: str) -> None:
        self.exposures[stimulus] = self.exposures.get(stimulus, 0) + 1

    def value(self, stimulus: str) -> float:
        return self.values.get(stimulus, 0.0)

    def novelty(self, stimulus: str) -> float:
        return 1.0 / (1.0 + self.habituation_rate * self.exposures.get(stimulus, 0))


class MemorySystem:
    def __init__(
        self, spatial: SpatialMemory, social: SocialMemory, episodic: EpisodicMemory, associations: AssociativeLearner
    ) -> None:
        self.spatial = spatial
        self.social = social
        self.episodic = episodic
        self.associations = associations

    def inherit_from(self, mother: MemorySystem, count: int, tick: int) -> None:
        for place in mother.spatial.strongest(count, tick):
            self.spatial.remember(place.kind, place.position, place.quality, tick, INHERITED_CONFIDENCE)
        for stimulus, value in mother.associations.values.items():
            if abs(value) > abs(self.associations.value(stimulus)):
                self.associations.values[stimulus] = value * INHERITED_CONFIDENCE
