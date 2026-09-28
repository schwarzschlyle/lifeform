from __future__ import annotations

from dataclasses import dataclass, field

PEDIGREE_DEPTH = 3


@dataclass(frozen=True, slots=True)
class Lineage:
    organism_id: int
    mother_id: int | None
    father_id: int | None
    generation: int
    ancestry: dict[int, tuple[int, float]] = field(default_factory=dict)

    @classmethod
    def founder(cls, organism_id: int) -> Lineage:
        return cls(organism_id, None, None, 0, {organism_id: (0, 1.0)})

    @classmethod
    def offspring(cls, organism_id: int, mother: Lineage, father: Lineage) -> Lineage:
        ancestry: dict[int, tuple[int, float]] = {organism_id: (0, 1.0)}
        for parent in (mother, father):
            for ancestor, (depth, contribution) in parent.ancestry.items():
                if depth + 1 > PEDIGREE_DEPTH:
                    continue
                previous = ancestry.get(ancestor)
                share = contribution * 0.5
                if previous is None:
                    ancestry[ancestor] = (depth + 1, share)
                else:
                    ancestry[ancestor] = (min(previous[0], depth + 1), previous[1] + share)
        generation = max(mother.generation, father.generation) + 1
        return cls(organism_id, mother.organism_id, father.organism_id, generation, ancestry)

    def relatedness(self, other: Lineage) -> float:
        shared = set(self.ancestry) & set(other.ancestry)
        if not shared:
            return 0.0
        closest = min(self.ancestry[ancestor][0] + other.ancestry[ancestor][0] for ancestor in shared)
        return min(
            1.0,
            sum(
                self.ancestry[ancestor][1] * other.ancestry[ancestor][1]
                for ancestor in shared
                if self.ancestry[ancestor][0] + other.ancestry[ancestor][0] == closest
            ),
        )
