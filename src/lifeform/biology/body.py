from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field

from lifeform.core.geometry import Direction, Position

MEAT_KEY = "meat"
PAIN_PER_DAMAGE = 2.0
LIMP_SEVERITY = 0.3
LEDGER_FLOOR = 1e-4


@dataclass(slots=True)
class Wound:
    severity: float
    bleeding: bool
    on_limb: bool
    source: str = "combat"


@dataclass(slots=True)
class CarriedFood:
    food_key: str
    mass_kg: float
    origin_species_id: int = -1


@dataclass(slots=True)
class DamageLedger:
    recent: dict[str, float] = field(default_factory=dict)

    def record(self, source: str, amount: float) -> None:
        self.recent[source] = self.recent.get(source, 0.0) + amount

    def dominant_source(self) -> str | None:
        if not self.recent:
            return None
        return max(self.recent, key=self.recent.__getitem__)

    def fade(self, retention: float) -> None:
        self.recent = {source: amount * retention for source, amount in self.recent.items() if amount > LEDGER_FLOOR}


@dataclass(slots=True)
class BodyState:
    position: Position
    heading: Direction
    mass_kg: float
    lean_mass_kg: float
    energy_eu: float
    hydration: float
    body_temperature_c: float
    health: float = 1.0
    thermal_strain: float = 0.0
    ticks_since_novelty: int = 0
    chased_by: int | None = None
    sleep_pressure: float = 0.2
    stamina: float = 1.0
    pain: float = 0.0
    fear: float = 0.0
    stress: float = 0.0
    parasite_load: float = 0.0
    toxin_load: float = 0.0
    age_ticks: int = 0
    stomach: dict[str, float] = field(default_factory=dict)
    wounds: list[Wound] = field(default_factory=list)
    carrying: CarriedFood | None = None
    asleep: bool = False
    hidden: bool = False
    in_den: bool = False
    climbing: bool = False
    braced: bool = False
    frozen: bool = False
    stalking: bool = False
    ambushing: bool = False
    playing_dead: bool = False
    dry_ticks: int = 0
    harassed_ticks: int = 0
    last_damage_tick: int = -1
    attacked_by: int | None = None
    certainty_bonus: float = 0.0
    radius_bonus: float = 0.0
    last_actions: deque[str] = field(default_factory=lambda: deque(maxlen=3))
    damage: DamageLedger = field(default_factory=DamageLedger)

    def stomach_total(self) -> float:
        return sum(self.stomach.values())

    def add_to_stomach(self, food_key: str, mass_kg: float) -> None:
        self.stomach[food_key] = self.stomach.get(food_key, 0.0) + mass_kg

    def take_damage(self, source: str, amount: float, tick: int) -> None:
        self.health = max(0.0, self.health - amount)
        self.damage.record(source, amount)
        self.pain = min(1.0, self.pain + amount * PAIN_PER_DAMAGE)
        self.last_damage_tick = tick

    @property
    def limping(self) -> bool:
        return any(wound.on_limb and wound.severity > LIMP_SEVERITY for wound in self.wounds)

    @property
    def bleeding(self) -> bool:
        return any(wound.bleeding for wound in self.wounds)

    def reset_postures(self) -> None:
        self.braced = False
        self.frozen = False
        self.stalking = False
        self.ambushing = False
        self.playing_dead = False
        self.hidden = False
