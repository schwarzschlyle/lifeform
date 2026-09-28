from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Instinct:
    key: str
    wording: str


INSTINCTS: tuple[Instinct, ...] = (
    Instinct("herd_cohesion", "feels safest close to others of its kind"),
    Instinct("freeze_first", "tends to freeze and stay still when it first senses danger"),
    Instinct("flee_early", "runs from big sharp-toothed animals at the first sign of them"),
    Instinct("mob_predators", "joins others of its kind to harass a predator"),
    Instinct("ambush_hunter", "hunts by waiting hidden near places prey visit"),
    Instinct("pursuit_hunter", "hunts by chasing prey over long distances"),
    Instinct("pack_hunting", "prefers to hunt alongside others of its kind"),
    Instinct("scavenging", "is drawn to the smell of carrion"),
    Instinct("food_caching", "stores spare food near its den"),
    Instinct("den_dwelling", "rests and sleeps in a den or burrow"),
    Instinct("water_affinity", "likes to stay near water"),
    Instinct("basking", "warms itself in the sun when cold"),
    Instinct("open_ground_wariness", "avoids open ground in daylight"),
    Instinct("territorial_marking", "marks and defends a home area"),
    Instinct("migration_urge", "feels an urge to travel far when the season turns"),
    Instinct("nest_building", "prepares a sheltered den before giving birth"),
    Instinct("infant_guarding", "stays close to its young and defends them"),
    Instinct("sentinel", "keeps watch while others of its kind feed"),
    Instinct("alarm_calling", "calls out loudly when it sees danger"),
    Instinct("food_sharing", "shares food with its close kin"),
    Instinct("play_dead", "goes limp and plays dead when caught"),
    Instinct("neophobia", "is wary of unfamiliar things"),
    Instinct("neophilia", "is drawn to new things and places"),
    Instinct("kleptoparasitism", "steals food from others when it can"),
)

INSTINCT_KEYS: tuple[str, ...] = tuple(instinct.key for instinct in INSTINCTS)
INSTINCT_BY_KEY: dict[str, Instinct] = {instinct.key: instinct for instinct in INSTINCTS}
