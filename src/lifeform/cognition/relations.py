from __future__ import annotations

from lifeform.actions.verbs import Verb
from lifeform.biology.mechanics import BodyMechanics
from lifeform.biology.organism import Organism
from lifeform.cognition.context import MindContext
from lifeform.cognition.vocabulary import DISTANCE, RELATIVE_SIZE, RELATIVE_SPEED, RecencyWords
from lifeform.perception.percepts import EntityPercept
from lifeform.world.entities import Carcass
from lifeform.world.terrain import TerrainType

UNCLEAR_CERTAINTY = 0.35
NAMED_CERTAINTY = 0.7
OVERPOWER_RATIO = 2.0
DOMINANCE_MARGIN = 50.0
ASSOCIATION_NOTABLE = 0.3
WOUNDED_HEALTH = 0.6
ALL_OUT_EFFORT = 3
ENDURANCE_DIFFERENCE = 1.0
SIBLING_RELATEDNESS = 0.45
HALF_SIBLING_RELATEDNESS = 0.2
RELATIVE_RELATEDNESS = 0.1
FRESH_SPOILAGE = 0.3
ROTTING_SPOILAGE = 0.7
MOSTLY_EATEN_FRACTION = 0.3
SMALL_ANIMAL_KG = 5.0
BIG_ANIMAL_KG = 40.0
HEAVY_WEAPONRY = 0.6
LIGHT_WEAPONRY = 0.3
ARMORED = 0.6
CARNIVORE_DIET = 0.5
DANGEROUS_DIET = 0.4
FASTER_BURST = 1.12
SLOWER_BURST = 0.9

PARTICIPLES: dict[str, str] = {
    Verb.MOVE: "walking",
    Verb.APPROACH: "moving toward something",
    Verb.FLEE: "running away",
    Verb.FOLLOW: "following another",
    Verb.STAY_WITH_GROUP: "moving with its group",
    Verb.GO_TO_MEMORY: "travelling",
    Verb.FOLLOW_SCENT: "following a scent",
    Verb.STALK: "creeping low",
    Verb.CHASE: "chasing",
    Verb.CLIMB: "climbing",
    Verb.DESCEND: "climbing down",
    Verb.ENTER_DEN: "entering a den",
    Verb.LEAVE_DEN: "leaving a den",
    Verb.GRAZE: "grazing",
    Verb.BROWSE: "browsing leaves",
    Verb.EAT_FRUIT: "eating fruit",
    Verb.FORAGE_SEEDS: "picking seeds",
    Verb.DIG_FOR_GRUBS: "digging",
    Verb.FEED_ON_ALGAE: "feeding in the water",
    Verb.EAT_FUNGI: "eating fungi",
    Verb.EAT_CARCASS: "feeding on a carcass",
    Verb.DRINK: "drinking",
    Verb.CARRY_FOOD: "carrying food",
    Verb.CACHE_FOOD: "burying food",
    Verb.DROP_FOOD: "dropping food",
    Verb.STEAL_FOOD: "snatching food",
    Verb.ATTACK: "attacking",
    Verb.AMBUSH: "lying still",
    Verb.FIGHT_BACK: "fighting",
    Verb.BRACE: "standing braced",
    Verb.THREAT_DISPLAY: "baring its teeth",
    Verb.MOB: "harassing a predator",
    Verb.CHALLENGE: "squaring up to a rival",
    Verb.SUBMIT: "cowering",
    Verb.HIDE: "hiding",
    Verb.FREEZE: "standing still",
    Verb.PLAY_DEAD: "lying limp",
    Verb.SCAN: "looking around",
    Verb.INVESTIGATE: "sniffing around",
    Verb.REST: "resting",
    Verb.SLEEP: "asleep",
    Verb.BASK: "basking in the sun",
    Verb.SEEK_SHADE: "seeking shade",
    Verb.HUDDLE: "huddling",
    Verb.WALLOW: "wallowing",
    Verb.GROOM_SELF: "grooming itself",
    Verb.DIG_DEN: "digging a burrow",
    Verb.GROOM: "grooming another",
    Verb.SHARE_FOOD: "sharing food",
    Verb.SCENT_MARK: "scent-marking",
    Verb.COURT: "displaying",
    Verb.MATE_WITH: "mating",
    Verb.NURSE: "nursing young",
    Verb.SUCKLE: "suckling",
    Verb.DEFEND_YOUNG: "guarding its young",
}


class RelationalFacts:
    def __init__(self, mechanics: BodyMechanics, recency: RecencyWords) -> None:
        self._mechanics = mechanics
        self._recency = recency

    def describe_animal(self, context: MindContext, percept: EntityPercept, target: Organism) -> dict[str, str]:
        description = {
            "id": percept.label,
            "what": self._identity(context, percept, target),
            "where": self._where(percept),
            "doing": self._doing(context, target),
        }
        facts = self._facts(context, percept, target)
        if facts:
            description["facts"] = "; ".join(facts)
        remembered = self._remembered(context, target)
        if remembered:
            description["you_remember"] = remembered
        return description

    def describe_carcass(self, context: MindContext, percept: EntityPercept, carcass: Carcass) -> dict[str, str]:
        kind = context.species_name(carcass.species_id) if percept.certainty >= NAMED_CERTAINTY else "an animal"
        freshness = (
            "fresh"
            if carcass.spoilage < FRESH_SPOILAGE
            else ("going off" if carcass.spoilage < ROTTING_SPOILAGE else "rotting")
        )
        size = RELATIVE_SIZE.word(carcass.mass_kg / max(context.organism.body.mass_kg, 1e-6))
        remaining = "mostly eaten" if carcass.remaining_fraction < MOSTLY_EATEN_FRACTION else "plenty of meat left"
        description = {
            "id": percept.label,
            "what": f"the carcass of {self._article(kind)}",
            "where": self._where(percept),
            "facts": f"{freshness}; {remaining}; the carcass is {size}",
        }
        if context.organism.memory.associations.value(f"species:{carcass.species_id}") < -ASSOCIATION_NOTABLE:
            description["you_remember"] = "you associate that kind with pain or sickness"
        return description

    def size_phrase(self, viewer: Organism, target: Organism) -> str:
        return RELATIVE_SIZE.word(target.body.mass_kg / max(viewer.body.mass_kg, 1e-6))

    @staticmethod
    def _where(percept: EntityPercept) -> str:
        return f"{DISTANCE.word(percept.distance)}, to the {percept.direction.word}"

    def _identity(self, context: MindContext, percept: EntityPercept, target: Organism) -> str:
        viewer = context.organism
        size = self.size_phrase(viewer, target)
        if percept.certainty < UNCLEAR_CERTAINTY:
            return f"an unclear shape, {size}"
        kin = self.kinship(viewer, target)
        if kin is not None:
            return kin
        if target.species_id == viewer.species_id:
            stage = (
                "a youngster" if not target.is_adult else ("a female" if target.reproduction.is_female else "a male")
            )
            return f"{stage} of your own kind"
        armament = self._armament(target)
        if percept.certainty >= NAMED_CERTAINTY and self._knows_species(viewer, target.species_id):
            return f"{self._article(armament)} animal, a {context.species_name(target.species_id)} ({size})"
        return f"{self._article(armament)} animal ({size})"

    def kinship(self, viewer: Organism, target: Organism) -> str | None:
        if target.id == viewer.reproduction.mother_id:
            return "your mother"
        if target.reproduction.mother_id == viewer.id:
            return "your young" if not target.reproduction.weaned else "your grown offspring"
        if target.id == viewer.lineage.father_id:
            return "your father"
        relatedness = viewer.lineage.relatedness(target.lineage)
        if relatedness >= SIBLING_RELATEDNESS:
            return "your sibling"
        if relatedness >= HALF_SIBLING_RELATEDNESS:
            return "your half-sibling"
        if relatedness >= RELATIVE_RELATEDNESS:
            return "a relative of yours"
        return None

    def _doing(self, context: MindContext, target: Organism) -> str:
        if target.body.asleep:
            return "asleep"
        if not target.body.last_actions:
            return "standing"
        last = target.body.last_actions[-1]
        activity = PARTICIPLES.get(last, "standing")
        heading_toward = context.world.metric.direction(target.position, context.organism.position)
        if target.body.heading == heading_toward and last in (Verb.APPROACH, Verb.CHASE, Verb.STALK, Verb.ATTACK):
            return "creeping toward you" if last == Verb.STALK else "coming toward you"
        return activity

    def _facts(self, context: MindContext, percept: EntityPercept, target: Organism) -> list[str]:
        viewer = context.organism
        facts: list[str] = []
        if target.species_id != viewer.species_id or target.is_adult:
            facts.append(self._speed_fact(viewer, target, context.tick))
        facts.extend(self._strength_facts(viewer, target))
        if not target.body.asleep:
            facts.append("has noticed you" if context.noticed(target.id, viewer.id) else "has not noticed you")
        facts.extend(self._state_facts(context, target))
        if self._water_between(context, target):
            facts.append("deep water lies between you")
        return [fact for fact in facts if fact]

    def _speed_fact(self, viewer: Organism, target: Organism, tick: int) -> str:
        burst = self._mechanics.top_speed(target, tick) / max(self._mechanics.top_speed(viewer, tick), 1)
        burst_word = RELATIVE_SPEED.word(burst)
        endurance_gap = target.phenotype.stamina_ticks - viewer.phenotype.stamina_ticks
        if burst > FASTER_BURST and endurance_gap < -ENDURANCE_DIFFERENCE:
            return f"{burst_word} over a short dash, but tires sooner"
        if burst < SLOWER_BURST and endurance_gap > ENDURANCE_DIFFERENCE:
            return f"{burst_word} over a short dash, but can run for longer"
        return burst_word

    def _strength_facts(self, viewer: Organism, target: Organism) -> list[str]:
        facts: list[str] = []
        threat = self._mechanics.attack_power(target, ALL_OUT_EFFORT) / max(self._mechanics.defense(viewer), 1e-6)
        advantage = self._mechanics.attack_power(viewer, ALL_OUT_EFFORT) / max(self._mechanics.defense(target), 1e-6)
        if threat > OVERPOWER_RATIO and target.phenotype.diet.animal > DANGEROUS_DIET:
            facts.append("could badly hurt you")
        if advantage > OVERPOWER_RATIO:
            facts.append("you could overpower it")
        if target.species_id == viewer.species_id and target.is_adult and viewer.is_adult:
            difference = target.social.rating - viewer.social.rating
            if difference > DOMINANCE_MARGIN:
                facts.append("dominates you")
            elif difference < -DOMINANCE_MARGIN:
                facts.append("you outrank it")
        return facts

    def _state_facts(self, context: MindContext, target: Organism) -> list[str]:
        viewer = context.organism
        facts: list[str] = []
        if target.body.health < WOUNDED_HEALTH:
            facts.append("wounded")
        if target.infection.infectious:
            facts.append("looks sick and is coughing")
        if target.body.carrying is not None:
            facts.append("carrying food")
        if target.body.playing_dead:
            facts.append("lying limp, seems dead")
        if target.body.climbing:
            facts.append("up in a tree")
        if not target.reproduction.weaned:
            facts.append("a helpless youngster" if self._mechanics.is_immobile_newborn(target) else "a youngster")
        same_kind = target.species_id == viewer.species_id
        if same_kind and target.reproduction.sex != viewer.reproduction.sex and context.mate_eligible(target):
            facts.append("ready to mate")
        if target.id in viewer.reproduction.courted_by:
            facts.append("is courting you")
        return facts

    def _water_between(self, context: MindContext, target: Organism) -> bool:
        world = context.world
        origin = context.organism.position
        dx, dy = world.metric.delta(origin, target.position)
        steps = max(abs(dx), abs(dy))
        for step in range(1, steps):
            position = world.metric.wrap(origin.x + round(dx * step / steps), origin.y + round(dy * step / steps))
            if world.terrain_at(position) == TerrainType.DEEP_WATER:
                return True
        return False

    def _remembered(self, context: MindContext, target: Organism) -> str | None:
        viewer = context.organism
        acquaintance = viewer.memory.social.relation_to(target.id)
        if acquaintance is not None and acquaintance.relation in ("attacker", "rival", "mate", "ally"):
            when = self._recency.word(context.tick - acquaintance.tick_seen)
            return {
                "attacker": f"this one attacked you ({when})",
                "rival": f"this one beat you in a contest ({when})",
                "mate": "you have mated with this one",
                "ally": "this one has groomed or shared food with you",
            }[acquaintance.relation]
        association = viewer.memory.associations.value(f"species:{target.species_id}")
        if target.species_id == viewer.species_id:
            return None
        if association < -ASSOCIATION_NOTABLE:
            strength = "strongly" if association < -2 * ASSOCIATION_NOTABLE else "somewhat"
            return f"you associate its kind with danger and pain ({strength})"
        if association > ASSOCIATION_NOTABLE:
            return "you associate its kind with a good meal"
        return None

    @staticmethod
    def _knows_species(viewer: Organism, species_id: int) -> bool:
        key = f"species:{species_id}"
        return viewer.memory.associations.exposures.get(key, 0) > 0

    @staticmethod
    def _armament(target: Organism) -> str:
        weapon = target.trait("weaponry")
        mass = target.body.mass_kg
        size = "small" if mass < SMALL_ANIMAL_KG else ("big" if mass > BIG_ANIMAL_KG else "medium-sized")
        if target.phenotype.diet.animal >= CARNIVORE_DIET:
            teeth = "sharp-toothed" if weapon < HEAVY_WEAPONRY else "big-fanged, clawed"
        elif weapon > HEAVY_WEAPONRY:
            teeth = "heavily horned"
        elif weapon > LIGHT_WEAPONRY:
            teeth = "horned"
        else:
            teeth = "blunt-toothed"
        armor = ", armored" if target.trait("armor") > ARMORED else ""
        return f"{size} {teeth}{armor}"

    @staticmethod
    def _article(phrase: str) -> str:
        return f"an {phrase}" if phrase[:1].lower() in "aeiou" else f"a {phrase}"
