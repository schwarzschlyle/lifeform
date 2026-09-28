from __future__ import annotations

from bisect import bisect_right
from dataclasses import dataclass

from lifeform.core.time import Calendar


@dataclass(frozen=True, slots=True)
class Quantizer:
    edges: tuple[float, ...]
    words: tuple[str, ...]

    def __post_init__(self) -> None:
        if len(self.words) != len(self.edges) + 1:
            raise ValueError("a quantizer needs exactly one more word than edges")

    def word(self, value: float) -> str:
        return self.words[bisect_right(self.edges, value)]


DISTANCE = Quantizer((1.5, 2.5, 4.5, 7.5, 12.5), ("beside you", "very near", "near", "mid-distance", "far", "very far"))
RELATIVE_SIZE = Quantizer(
    (0.1, 0.33, 0.8, 1.25, 3.0, 10.0),
    (
        "tiny next to you",
        "much smaller than you",
        "smaller than you",
        "about your size",
        "bigger than you",
        "much bigger than you",
        "enormous next to you",
    ),
)
RELATIVE_SPEED = Quantizer(
    (0.6, 0.9, 1.12, 1.6),
    ("much slower than you", "slower than you", "about as fast as you", "faster than you", "much faster than you"),
)
GROUP_SIZE = Quantizer((1.5, 2.5, 5.5, 10.5), ("one", "a pair", "a few", "about six to ten", "a large group"))
SCENT_INTENSITY = Quantizer((3.0, 10.0, 30.0), ("faint", "clear", "strong", "overwhelming"))
LOUDNESS = Quantizer((6.0, 18.0, 30.0), ("faint", "clear", "loud", "deafening"))
FOOD_AMOUNT = Quantizer((0.1, 0.6, 2.0, 5.0), ("almost none", "sparse", "some", "plenty", "lush"))
HEALTH = Quantizer((0.15, 0.4, 0.7, 0.92), ("near death", "badly wounded", "wounded", "slightly hurt", "healthy"))
HUNGER = Quantizer((0.15, 0.35, 0.6, 0.85), ("not hungry", "peckish", "hungry", "very hungry", "starving"))
THIRST = Quantizer((0.15, 0.35, 0.6, 0.85), ("not thirsty", "slightly thirsty", "thirsty", "very thirsty", "parched"))
SLEEPINESS = Quantizer((0.3, 0.5, 0.7, 0.85), ("alert", "a little tired", "tired", "very tired", "exhausted"))
THERMAL = Quantizer((-0.6, -0.2, 0.2, 0.6), ("freezing", "cold", "comfortable", "warm", "overheating"))
PAIN = Quantizer((0.05, 0.25, 0.5, 0.8), ("none", "mild", "sharp", "severe", "agonizing"))
FEAR = Quantizer((0.2, 0.45, 0.75), ("calm", "uneasy", "afraid", "terrified"))
URGE_TO_MATE = Quantizer((0.05, 0.5, 0.8), ("none", "mild", "strong", "overwhelming"))
COVER = Quantizer((0.15, 0.4, 0.7), ("no cover", "a little cover", "good cover", "thick cover"))
SNOW = Quantizer((5.0, 30.0, 80.0), ("no snow", "a light snow cover", "deep snow", "very deep snow"))
INSTINCT_STRENGTH = Quantizer((0.75,), ("somewhat", "strongly"))

TEMPERAMENT_WORDS: dict[str, tuple[str, str, str, str]] = {
    "boldness": ("very timid", "timid", "bold", "fearless"),
    "curiosity": ("incurious", "uninterested in novelty", "curious", "very curious"),
    "sociability": ("strictly solitary", "prefers solitude", "sociable", "highly social"),
    "aggression": ("very peaceable", "peaceable", "quick to fight", "very aggressive"),
    "vigilance": ("inattentive", "easygoing", "watchful", "hyper-vigilant"),
    "patience": ("very restless", "restless", "patient", "extremely patient"),
    "altruism": ("selfish", "self-serving", "generous to kin", "devoted to kin"),
    "territoriality": ("nomadic", "roaming", "homebound", "fiercely territorial"),
    "parental_care": (
        "leaves its young to fend for themselves",
        "a casual parent",
        "an attentive parent",
        "a devoted parent",
    ),
    "mate_choosiness": ("mates with any partner", "not very choosy", "choosy about mates", "very choosy about mates"),
}
TEMPERAMENT_EDGES: tuple[float, float, float, float] = (0.15, 0.35, 0.65, 0.85)


def temperament_word(trait: str, value: float) -> str | None:
    very_low, low, high, very_high = TEMPERAMENT_WORDS[trait]
    lowest, lower, upper, uppermost = TEMPERAMENT_EDGES
    if value < lowest:
        return very_low
    if value < lower:
        return low
    if value <= upper:
        return None
    return high if value <= uppermost else very_high


class RecencyWords:
    def __init__(self, calendar: Calendar) -> None:
        self._calendar = calendar

    def word(self, ticks_ago: int) -> str:
        days = self._calendar.days(ticks_ago)
        if ticks_ago <= 1:
            return "just now"
        if days < 1.0:
            return "earlier today"
        if days < 2.0:
            return "yesterday"
        if days < 4.0:
            return "two or three days ago"
        return "many days ago"


def activity_word(activity_phase: float) -> str:
    if activity_phase < 0.3:
        return "a creature of the night"
    if activity_phase < 0.7:
        return "most active at dawn and dusk"
    return "active by day"
