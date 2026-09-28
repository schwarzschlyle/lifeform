from __future__ import annotations

from typing import NewType

OrganismId = NewType("OrganismId", int)
SpeciesId = NewType("SpeciesId", int)
CarcassId = NewType("CarcassId", int)
DenId = NewType("DenId", int)
StrainId = NewType("StrainId", int)


class IdSequence:
    def __init__(self, start: int = 1) -> None:
        self._next = start

    def next(self) -> int:
        issued = self._next
        self._next += 1
        return issued

    @property
    def peek(self) -> int:
        return self._next
