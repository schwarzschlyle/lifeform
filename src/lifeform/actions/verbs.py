from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class VerbFamily(StrEnum):
    LOCOMOTION = "locomotion"
    FORAGING = "foraging"
    COMBAT = "combat"
    CONCEALMENT = "concealment"
    BODY_CARE = "body_care"
    SOCIAL = "social"
    REPRODUCTION = "reproduction"


class Verb(StrEnum):
    MOVE = "move"
    APPROACH = "approach"
    FLEE = "flee"
    FOLLOW = "follow"
    STAY_WITH_GROUP = "stay_with_group"
    GO_TO_MEMORY = "go_to_memory"
    FOLLOW_SCENT = "follow_scent"
    STALK = "stalk"
    CHASE = "chase"
    CLIMB = "climb"
    DESCEND = "descend"
    ENTER_DEN = "enter_den"
    LEAVE_DEN = "leave_den"
    GRAZE = "graze"
    BROWSE = "browse"
    EAT_FRUIT = "eat_fruit"
    FORAGE_SEEDS = "forage_seeds"
    DIG_FOR_GRUBS = "dig_for_grubs"
    FEED_ON_ALGAE = "feed_on_algae"
    EAT_FUNGI = "eat_fungi"
    EAT_CARCASS = "eat_carcass"
    DRINK = "drink"
    CARRY_FOOD = "carry_food"
    CACHE_FOOD = "cache_food"
    DROP_FOOD = "drop_food"
    STEAL_FOOD = "steal_food"
    ATTACK = "attack"
    AMBUSH = "ambush"
    FIGHT_BACK = "fight_back"
    BRACE = "brace"
    THREAT_DISPLAY = "threat_display"
    MOB = "mob"
    CHALLENGE = "challenge"
    SUBMIT = "submit"
    HIDE = "hide"
    FREEZE = "freeze"
    PLAY_DEAD = "play_dead"
    SCAN = "scan_surroundings"
    INVESTIGATE = "investigate"
    REST = "rest"
    SLEEP = "sleep"
    BASK = "bask"
    SEEK_SHADE = "seek_shade"
    HUDDLE = "huddle"
    WALLOW = "wallow"
    GROOM_SELF = "groom_self"
    DIG_DEN = "dig_den"
    GROOM = "groom"
    SHARE_FOOD = "share_food"
    SCENT_MARK = "scent_mark"
    COURT = "court"
    MATE_WITH = "mate_with"
    NURSE = "nurse"
    SUCKLE = "suckle"
    DEFEND_YOUNG = "defend_young"


@dataclass(frozen=True, slots=True)
class VerbSpec:
    verb: Verb
    family: VerbFamily
    pal: float
    moves: bool
    past_tense: str


_L, _F, _C, _H = VerbFamily.LOCOMOTION, VerbFamily.FORAGING, VerbFamily.COMBAT, VerbFamily.CONCEALMENT
_B, _S, _R = VerbFamily.BODY_CARE, VerbFamily.SOCIAL, VerbFamily.REPRODUCTION

VERB_SPECS: dict[Verb, VerbSpec] = {
    spec.verb: spec
    for spec in (
        VerbSpec(Verb.MOVE, _L, 1.5, True, "walked"),
        VerbSpec(Verb.APPROACH, _L, 1.5, True, "approached something"),
        VerbSpec(Verb.FLEE, _L, 2.0, True, "fled"),
        VerbSpec(Verb.FOLLOW, _L, 1.5, True, "followed another"),
        VerbSpec(Verb.STAY_WITH_GROUP, _L, 1.4, True, "kept with the group"),
        VerbSpec(Verb.GO_TO_MEMORY, _L, 1.5, True, "travelled to a remembered place"),
        VerbSpec(Verb.FOLLOW_SCENT, _L, 1.5, True, "followed a scent"),
        VerbSpec(Verb.STALK, _L, 1.6, True, "stalked"),
        VerbSpec(Verb.CHASE, _L, 2.5, True, "chased"),
        VerbSpec(Verb.CLIMB, _L, 2.0, False, "climbed a tree"),
        VerbSpec(Verb.DESCEND, _L, 1.5, False, "climbed down"),
        VerbSpec(Verb.ENTER_DEN, _L, 1.1, False, "went into the den"),
        VerbSpec(Verb.LEAVE_DEN, _L, 1.1, False, "left the den"),
        VerbSpec(Verb.GRAZE, _F, 1.5, False, "grazed"),
        VerbSpec(Verb.BROWSE, _F, 1.5, False, "browsed"),
        VerbSpec(Verb.EAT_FRUIT, _F, 1.4, False, "ate fruit"),
        VerbSpec(Verb.FORAGE_SEEDS, _F, 1.5, False, "foraged seeds"),
        VerbSpec(Verb.DIG_FOR_GRUBS, _F, 1.8, False, "dug for grubs"),
        VerbSpec(Verb.FEED_ON_ALGAE, _F, 1.5, False, "fed on algae"),
        VerbSpec(Verb.EAT_FUNGI, _F, 1.3, False, "ate fungi"),
        VerbSpec(Verb.EAT_CARCASS, _F, 1.6, False, "fed on a carcass"),
        VerbSpec(Verb.DRINK, _F, 1.2, False, "drank"),
        VerbSpec(Verb.CARRY_FOOD, _F, 1.5, False, "picked up food"),
        VerbSpec(Verb.CACHE_FOOD, _F, 1.2, False, "cached food"),
        VerbSpec(Verb.DROP_FOOD, _F, 1.0, False, "dropped food"),
        VerbSpec(Verb.STEAL_FOOD, _F, 2.5, True, "tried to steal food"),
        VerbSpec(Verb.ATTACK, _C, 4.0, True, "attacked"),
        VerbSpec(Verb.AMBUSH, _C, 1.2, False, "lay in ambush"),
        VerbSpec(Verb.FIGHT_BACK, _C, 3.5, False, "fought back"),
        VerbSpec(Verb.BRACE, _C, 1.5, False, "braced to fight"),
        VerbSpec(Verb.THREAT_DISPLAY, _C, 1.8, False, "made a threat display"),
        VerbSpec(Verb.MOB, _C, 2.5, True, "mobbed a predator"),
        VerbSpec(Verb.CHALLENGE, _C, 2.0, True, "challenged a rival"),
        VerbSpec(Verb.SUBMIT, _C, 1.0, False, "submitted"),
        VerbSpec(Verb.HIDE, _H, 1.1, False, "hid"),
        VerbSpec(Verb.FREEZE, _H, 1.0, False, "froze"),
        VerbSpec(Verb.PLAY_DEAD, _H, 1.0, False, "played dead"),
        VerbSpec(Verb.SCAN, _H, 1.2, False, "looked around"),
        VerbSpec(Verb.INVESTIGATE, _H, 1.4, True, "investigated"),
        VerbSpec(Verb.REST, _B, 1.1, False, "rested"),
        VerbSpec(Verb.SLEEP, _B, 0.9, False, "slept"),
        VerbSpec(Verb.BASK, _B, 1.0, False, "basked in the sun"),
        VerbSpec(Verb.SEEK_SHADE, _B, 1.2, True, "sought shade"),
        VerbSpec(Verb.HUDDLE, _B, 1.0, False, "huddled with others"),
        VerbSpec(Verb.WALLOW, _B, 1.3, False, "wallowed"),
        VerbSpec(Verb.GROOM_SELF, _B, 1.1, False, "groomed itself"),
        VerbSpec(Verb.DIG_DEN, _B, 2.5, False, "dug at a den"),
        VerbSpec(Verb.GROOM, _S, 1.2, False, "groomed another"),
        VerbSpec(Verb.SHARE_FOOD, _S, 1.1, False, "shared food"),
        VerbSpec(Verb.SCENT_MARK, _S, 1.2, False, "scent-marked"),
        VerbSpec(Verb.COURT, _R, 2.0, True, "courted"),
        VerbSpec(Verb.MATE_WITH, _R, 2.0, False, "mated"),
        VerbSpec(Verb.NURSE, _R, 1.3, False, "nursed its young"),
        VerbSpec(Verb.SUCKLE, _R, 1.0, False, "suckled"),
        VerbSpec(Verb.DEFEND_YOUNG, _R, 1.5, True, "guarded its young"),
    )
}

VERB_ORDER: tuple[Verb, ...] = tuple(Verb)
VERB_CODE: dict[Verb, int] = {verb: index for index, verb in enumerate(VERB_ORDER)}
STALLED_CODE = len(VERB_ORDER)
