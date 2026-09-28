from __future__ import annotations

from dataclasses import dataclass

from lifeform.biology.body import BodyState
from lifeform.biology.disease import InfectionState
from lifeform.biology.genome import Genome
from lifeform.biology.lineage import Lineage
from lifeform.biology.phenotype import Phenotype
from lifeform.biology.reproduction import ReproductiveState
from lifeform.biology.social import SocialState
from lifeform.core.geometry import Position
from lifeform.perception.memory import MemorySystem


@dataclass(slots=True)
class OrganismIdentity:
    organism_id: int
    name: str
    species_id: int
    birth_tick: int
    archetype: str | None


@dataclass(slots=True)
class Organism:
    identity: OrganismIdentity
    genome: Genome
    phenotype: Phenotype
    body: BodyState
    reproduction: ReproductiveState
    infection: InfectionState
    social: SocialState
    lineage: Lineage
    memory: MemorySystem
    alive: bool = True
    death_tick: int | None = None
    death_cause: str | None = None

    @property
    def id(self) -> int:
        return self.identity.organism_id

    @property
    def species_id(self) -> int:
        return self.identity.species_id

    @property
    def position(self) -> Position:
        return self.body.position

    @property
    def is_adult(self) -> bool:
        return self.reproduction.mature

    @property
    def is_dependent(self) -> bool:
        return not self.reproduction.weaned

    def trait(self, name: str) -> float:
        return self.phenotype.trait(name)

    def die(self, tick: int, cause: str) -> None:
        self.alive = False
        self.death_tick = tick
        self.death_cause = cause
