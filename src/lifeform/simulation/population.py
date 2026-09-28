from __future__ import annotations

import math
from collections import defaultdict

from lifeform.biology.organism import Organism
from lifeform.core.geometry import Position, TorusMetric

BUCKET_SIZE = 8


class Population:
    def __init__(self, metric: TorusMetric) -> None:
        self._metric = metric
        self.organisms: dict[int, Organism] = {}
        self.deceased: dict[int, Organism] = {}
        self._buckets: dict[tuple[int, int], list[Organism]] = defaultdict(list)
        self._columns = math.ceil(metric.width / BUCKET_SIZE)
        self._rows = math.ceil(metric.height / BUCKET_SIZE)

    def add(self, organism: Organism) -> None:
        self.organisms[organism.id] = organism
        self._buckets[self._bucket(organism.position)].append(organism)

    def get(self, organism_id: int | None) -> Organism | None:
        if organism_id is None:
            return None
        return self.organisms.get(organism_id)

    def any(self, organism_id: int | None) -> Organism | None:
        if organism_id is None:
            return None
        return self.organisms.get(organism_id) or self.deceased.get(organism_id)

    def living(self) -> list[Organism]:
        return [self.organisms[organism_id] for organism_id in sorted(self.organisms)]

    def __len__(self) -> int:
        return len(self.organisms)

    def retire(self, organism: Organism) -> None:
        self.organisms.pop(organism.id, None)
        self.deceased[organism.id] = organism

    def forget_deceased(self) -> None:
        self.deceased.clear()

    def reindex(self) -> None:
        self._buckets = defaultdict(list)
        for organism in self.organisms.values():
            self._buckets[self._bucket(organism.position)].append(organism)

    def within(self, position: Position, radius: float) -> list[Organism]:
        reach = math.ceil(radius / BUCKET_SIZE)
        column, row = self._bucket(position)
        seen: set[tuple[int, int]] = set()
        found: list[Organism] = []
        for row_step in range(-reach, reach + 1):
            for column_step in range(-reach, reach + 1):
                bucket = ((column + column_step) % self._columns, (row + row_step) % self._rows)
                if bucket in seen:
                    continue
                seen.add(bucket)
                found.extend(
                    organism
                    for organism in self._buckets.get(bucket, ())
                    if self._metric.distance(position, organism.position) <= radius
                )
        return found

    def species_counts(self) -> dict[int, int]:
        counts: dict[int, int] = defaultdict(int)
        for organism in self.organisms.values():
            counts[organism.species_id] += 1
        return dict(counts)

    def _bucket(self, position: Position) -> tuple[int, int]:
        return position.x // BUCKET_SIZE, position.y // BUCKET_SIZE
