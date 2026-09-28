from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from lifeform.actions.verbs import Verb
from lifeform.biology.drives import DriveState
from lifeform.biology.mechanics import BodyMechanics
from lifeform.biology.organism import Organism
from lifeform.cognition.context import MindContext
from lifeform.cognition.relations import RelationalFacts
from lifeform.cognition.vocabulary import DISTANCE, FOOD_AMOUNT, RecencyWords
from lifeform.config.parameters import EcologyParameters
from lifeform.core.geometry import Direction, Position
from lifeform.perception.forage_view import ForageView
from lifeform.perception.memory import PlaceMemory
from lifeform.perception.percepts import EntityKind, EntityPercept
from lifeform.world.terrain import TERRAIN, FoodLayer, TerrainType

MIN_FOOD_KG = 0.01
MIN_DIET_WEIGHT = 0.08
HIDING_COVER = 0.3
SHADE_CANOPY = 0.4
BASKING_LIGHT = 0.5
PARASITE_NOTICEABLE = 0.1
UNCERTAIN_IDENTITY = 0.7
PREDATORY_DIET = 0.3
DISPLAY_RANGE = 3.0
COURT_RANGE = 2.5
CHALLENGE_RANGE = 2.5
ADJACENT = 1.5
YOUNG_GUARD_RANGE = 2.5
CARRY_MASS_FRACTION = 0.15
MEMORY_OPTIONS = 3
SCENT_OPTIONS = 2
SOUND_OPTIONS = 2
NEED_THRESHOLD = 0.2
DANGEROUS = 0.3
ALLY_RANGE = 2.5
ALL_OUT_EFFORT = 3
UNCLEAR_SHAPE_CERTAINTY = 0.35
ADULT_ONLY_VERBS = frozenset(
    {
        Verb.CHALLENGE,
        Verb.COURT,
        Verb.MATE_WITH,
        Verb.THREAT_DISPLAY,
        Verb.SCENT_MARK,
        Verb.DIG_DEN,
        Verb.MOB,
        Verb.ATTACK,
        Verb.STALK,
        Verb.CHASE,
        Verb.AMBUSH,
        Verb.CARRY_FOOD,
        Verb.STEAL_FOOD,
        Verb.NURSE,
        Verb.SHARE_FOOD,
    }
)
ECTOTHERM_BASKING = 0.7

FOOD_VERBS: dict[FoodLayer, Verb] = {
    FoodLayer.GRASS: Verb.GRAZE,
    FoodLayer.BROWSE: Verb.BROWSE,
    FoodLayer.FRUIT: Verb.EAT_FRUIT,
    FoodLayer.SEEDS: Verb.FORAGE_SEEDS,
    FoodLayer.INVERTEBRATES: Verb.DIG_FOR_GRUBS,
    FoodLayer.ALGAE: Verb.FEED_ON_ALGAE,
    FoodLayer.FUNGI: Verb.EAT_FUNGI,
}
FOOD_PHRASES: dict[FoodLayer, str] = {
    FoodLayer.GRASS: "graze the grass here",
    FoodLayer.BROWSE: "browse the leaves and twigs here",
    FoodLayer.FRUIT: "eat the fruit here",
    FoodLayer.SEEDS: "pick seeds from the ground here",
    FoodLayer.INVERTEBRATES: "dig for grubs and insects here",
    FoodLayer.ALGAE: "feed on water plants here",
    FoodLayer.FUNGI: "eat the fungi here",
}
MEMORY_PHRASES: dict[str, str] = {
    "water": "water",
    "den": "your den",
    "refuge": "a safe hiding place",
    "danger": "a dangerous place",
    "meat": "a carcass",
}
ALARMING_SOUNDS = ("alarm_call", "distress_call", "warning_growl", "fight", "scream")


class TargetKind(StrEnum):
    NONE = "none"
    ANIMAL = "animal"
    CARCASS = "carcass"
    SCENT = "scent"
    SOUND = "sound"
    MEMORY = "memory"
    DIRECTION = "direction"


@dataclass(frozen=True, slots=True)
class Affordance:
    key: str
    verb: Verb
    description: str
    relevance: float = 0.0
    core: bool = False
    target_kind: TargetKind = TargetKind.NONE
    target_id: int | None = None
    direction: Direction | None = None
    destination: Position | None = None
    food_key: str | None = None


@dataclass(frozen=True, slots=True)
class RelevanceWeights:
    thirst_urgency: float = 1.5
    territory: float = 0.3
    leave_den: float = 0.2
    climb_down: float = 0.2
    den_instinct: float = 0.3
    den_pregnancy: float = 0.3
    caching: float = 0.3
    drop_food: float = 0.05
    suckle_bonus: float = 0.3
    play_dead: float = 0.5
    flee_danger: float = 2.0
    fight_back_base: float = 1.0
    steal_base: float = 0.5
    curiosity_approach: float = 0.3
    prey_approach: float = 0.5
    investigate: float = 0.8
    defensive_attack: float = 0.3
    follow_kin: float = 0.5
    follow_mother: float = 1.0
    groom_social: float = 0.2
    nurse_base: float = 0.5
    share_kin: float = 2.0
    challenge: float = 0.6
    submit: float = 0.5
    accept_mate: float = 1.5
    carcass: float = 1.5
    carry: float = 0.3
    investigate_sound: float = 0.5
    herd: float = 0.5
    foraging_move: float = 0.8


class AffordanceGenerator:
    def __init__(
        self,
        ecology: EcologyParameters,
        mechanics: BodyMechanics,
        relations: RelationalFacts,
        recency: RecencyWords,
        forage_view: ForageView,
        weights: RelevanceWeights | None = None,
    ) -> None:
        self._forage_view = forage_view
        self._weights = weights or RelevanceWeights()
        self._ecology = ecology
        self._mechanics = mechanics
        self._relations = relations
        self._recency = recency

    def generate(self, context: MindContext) -> list[Affordance]:
        candidates = [
            *self._core(context),
            *self._here(context),
            *self._entities(context),
            *self._scents(context),
            *self._sounds(context),
            *self._memories(context),
            *self._group(context),
        ]
        return self._select(candidates, dependent=not context.organism.reproduction.weaned)

    def _select(self, candidates: list[Affordance], dependent: bool) -> list[Affordance]:
        unique: dict[str, Affordance] = {}
        for affordance in candidates:
            if dependent and affordance.verb in ADULT_ONLY_VERBS:
                continue
            if affordance.key not in unique:
                unique[affordance.key] = affordance
        core = [affordance for affordance in unique.values() if affordance.core]
        optional = sorted(
            (affordance for affordance in unique.values() if not affordance.core), key=_relevance, reverse=True
        )
        room = max(0, self._ecology.cognition.max_menu_options - len(core))
        return core + optional[:room]

    def _core(self, context: MindContext) -> list[Affordance]:
        organism = context.organism
        world = context.world
        cover = world.cover(organism.position)
        sleep_place = (
            "in your den" if organism.body.in_den else ("in cover" if cover >= HIDING_COVER else "in the open")
        )
        core = [
            Affordance("rest", Verb.REST, "rest where you are", core=True),
            Affordance("sleep", Verb.SLEEP, f"sleep here, {sleep_place}", context.drives.sleepiness, core=True),
            Affordance("scan_surroundings", Verb.SCAN, "stop and look around carefully", core=True),
            Affordance("freeze", Verb.FREEZE, "stand completely still", core=True),
            Affordance("brace", Verb.BRACE, "brace yourself to fight off an attack", core=True),
        ]
        if cover >= HIDING_COVER or organism.body.in_den:
            core.append(Affordance("hide", Verb.HIDE, "hide in the cover here", core=True))
        if self._mechanics.top_speed(organism, context.tick) > 0 and not organism.body.in_den:
            core.extend(self._moves(context))
        return core

    def _moves(self, context: MindContext) -> list[Affordance]:
        organism = context.organism
        world = context.world
        swim = organism.trait("swim_skill")
        moves: list[Affordance] = []
        for direction in Direction:
            step = world.metric.step(organism.position, direction)
            if not world.is_passable(step, swim):
                continue
            terrain = world.terrain_at(step)
            verb_word = (
                "swim"
                if terrain == TerrainType.DEEP_WATER
                else ("wade" if terrain == TerrainType.SHALLOW_WATER else "walk")
            )
            food = self._forage_view.assess(organism, world, step).value
            food_words = f"; {FOOD_AMOUNT.word(food)} food for you" if food > 0.0 else "; nothing you can eat"
            moves.append(
                Affordance(
                    f"move_{direction.key}",
                    Verb.MOVE,
                    f"{verb_word} {direction.word} ({TERRAIN.description(terrain)}{food_words})",
                    context.drives.hunger * min(1.0, food) * self._weights.foraging_move,
                    core=True,
                    target_kind=TargetKind.DIRECTION,
                    direction=direction,
                )
            )
        return moves

    def _here(self, context: MindContext) -> list[Affordance]:
        return [
            *self._food_here(context),
            *self._water_here(context),
            *self._comfort_here(context),
            *self._den_and_tree(context),
            *self._care_here(context),
            *self._defense_here(context),
        ]

    def _food_here(self, context: MindContext) -> list[Affordance]:
        organism = context.organism
        world = context.world
        position = organism.position
        snow = float(world.fields.hydrology.snow_depth[position.y, position.x])
        bite = self._mechanics.bite_capacity(organism)
        options: list[Affordance] = []
        for layer, verb in FOOD_VERBS.items():
            diet_weight = organism.phenotype.diet.weight(self._ecology.food_layers[layer.key].diet_class)
            cached = sum(cache.mass_kg for cache in world.caches.at(position) if cache.layer_key == layer.key)
            amount = world.fields.vegetation.accessible(layer, position.x, position.y, snow) + cached
            if amount < MIN_FOOD_KG or diet_weight < MIN_DIET_WEIGHT:
                continue
            amount_word = FOOD_AMOUNT.word(amount / max(bite, 1e-6))
            options.append(
                Affordance(
                    f"{verb.value}_here",
                    verb,
                    f"{FOOD_PHRASES[layer]} ({amount_word})",
                    context.drives.hunger * diet_weight * min(1.0, amount / bite),
                    food_key=layer.key,
                )
            )
        return options

    def _water_here(self, context: MindContext) -> list[Affordance]:
        source = context.world.drinkable_near(context.organism.position)
        if source is None:
            return []
        place = "here" if source == context.organism.position else "beside you"
        return [
            Affordance(
                "drink",
                Verb.DRINK,
                f"drink from the water {place}",
                context.drives.thirst * self._weights.thirst_urgency,
                destination=source,
            )
        ]

    def _comfort_here(self, context: MindContext) -> list[Affordance]:
        organism = context.organism
        world = context.world
        position = organism.position
        drives = context.drives
        options: list[Affordance] = []
        if world.light(position) > BASKING_LIGHT and organism.phenotype.endothermy < ECTOTHERM_BASKING:
            options.append(Affordance("bask", Verb.BASK, "bask in the sunshine to warm up", max(0.0, -drives.thermal)))
        shade = self._shade_near(context)
        if shade is not None:
            options.append(
                Affordance(
                    "seek_shade",
                    Verb.SEEK_SHADE,
                    "move into the shade to cool down",
                    max(0.0, drives.thermal),
                    destination=shade,
                )
            )
        wet = [
            candidate
            for candidate in (position, *world.metric.neighbors(position))
            if world.terrain_at(candidate) in (TerrainType.WETLAND, TerrainType.SHALLOW_WATER)
        ]
        if wet:
            options.append(
                Affordance(
                    "wallow",
                    Verb.WALLOW,
                    "wallow in the mud or shallows to cool off and clean",
                    max(0.0, drives.thermal) + organism.body.parasite_load,
                    destination=wet[0],
                )
            )
        if any(context.world.metric.are_adjacent(position, other.position) for other in context.group):
            options.append(
                Affordance(
                    "huddle_with_group",
                    Verb.HUDDLE,
                    "huddle against others of your kind for warmth",
                    max(0.0, -drives.thermal),
                )
            )
        if organism.body.parasite_load > PARASITE_NOTICEABLE:
            options.append(
                Affordance(
                    "groom_self", Verb.GROOM_SELF, "groom yourself to get rid of parasites", organism.body.parasite_load
                )
            )
        if organism.is_adult:
            options.append(
                Affordance(
                    "scent_mark",
                    Verb.SCENT_MARK,
                    "leave your scent to mark this area as yours",
                    self._weights.territory * organism.trait("territoriality"),
                )
            )
        return options

    def _shade_near(self, context: MindContext) -> Position | None:
        world = context.world
        position = context.organism.position
        for candidate in (position, *world.metric.neighbors(position)):
            shaded = world.canopy(candidate) >= SHADE_CANOPY or world.terrain_at(candidate) in (
                TerrainType.ROCK,
                TerrainType.CAVE,
            )
            if shaded and world.is_passable(candidate, context.organism.trait("swim_skill")):
                return candidate
        return None

    def _den_and_tree(self, context: MindContext) -> list[Affordance]:
        organism = context.organism
        world = context.world
        position = organism.position
        drives = context.drives
        options: list[Affordance] = []
        den_here = world.dens.at(position)
        shelter_need = max(drives.sleepiness, drives.fear, 0.0, -drives.thermal)
        if organism.body.in_den:
            options.append(Affordance("leave_den", Verb.LEAVE_DEN, "come out of the den", self._weights.leave_den))
        elif den_here is not None and den_here.owner_id in (organism.id, organism.reproduction.mother_id):
            options.append(Affordance("enter_den", Verb.ENTER_DEN, "go into your den", shelter_need))
        terrain = world.terrain_at(position)
        if self._mechanics.can_dig(organism) and TERRAIN[terrain].diggable and den_here is None:
            options.append(
                Affordance(
                    "dig_den",
                    Verb.DIG_DEN,
                    "dig a den here (takes several hours of work)",
                    self._weights.den_instinct * organism.phenotype.instincts.get("den_dwelling", 0.0)
                    + self._weights.den_pregnancy * float(organism.reproduction.pregnancy is not None),
                )
            )
        if organism.body.climbing:
            options.append(Affordance("climb_down", Verb.DESCEND, "climb down from the tree", self._weights.climb_down))
        elif terrain in (TerrainType.FOREST, TerrainType.RAINFOREST) and self._mechanics.can_climb(organism):
            options.append(Affordance("climb_tree", Verb.CLIMB, "climb up into a tree", drives.fear))
        return options

    def _care_here(self, context: MindContext) -> list[Affordance]:
        organism = context.organism
        world = context.world
        options: list[Affordance] = []
        carried = organism.body.carrying
        if carried is not None:
            options.append(
                Affordance(
                    "cache_food",
                    Verb.CACHE_FOOD,
                    f"hide the {carried.food_key} you carry here",
                    self._weights.caching * organism.phenotype.instincts.get("food_caching", 0.0),
                )
            )
            options.append(
                Affordance(
                    "drop_food", Verb.DROP_FOOD, f"drop the {carried.food_key} you carry", self._weights.drop_food
                )
            )
        mother = context.animals(organism.reproduction.mother_id) if organism.reproduction.mother_id else None
        nursing_mother = (
            mother is not None
            and mother.alive
            and mother.reproduction.lactating
            and world.metric.are_adjacent(organism.position, mother.position)
        )
        if not organism.reproduction.weaned and nursing_mother:
            options.append(
                Affordance(
                    "suckle",
                    Verb.SUCKLE,
                    "suckle milk from your mother",
                    context.drives.hunger + self._weights.suckle_bonus,
                )
            )
        young_near = [
            young_id
            for young_id in organism.reproduction.dependents
            if (young := context.animals(young_id)) is not None
            and young.alive
            and world.metric.distance(organism.position, young.position) <= YOUNG_GUARD_RANGE
        ]
        if young_near:
            options.append(
                Affordance(
                    "defend_young",
                    Verb.DEFEND_YOUNG,
                    "stand guard over your young, ready to fight",
                    context.drives.fear * organism.trait("parental_care"),
                )
            )
        return options

    def _defense_here(self, context: MindContext) -> list[Affordance]:
        organism = context.organism
        options: list[Affordance] = []
        attacker_id = organism.body.attacked_by
        threatened = attacker_id is not None or any(
            percept.touching and percept.danger > DANGEROUS for percept in context.field.entities
        )
        if threatened:
            options.append(
                Affordance(
                    "play_dead", Verb.PLAY_DEAD, "go limp and play dead", context.drives.fear * self._weights.play_dead
                )
            )
        cover = context.world.cover(organism.position)
        hidden_enough = cover >= HIDING_COVER or organism.body.hidden
        if hidden_enough and organism.phenotype.diet.animal >= PREDATORY_DIET:
            options.append(
                Affordance(
                    "ambush",
                    Verb.AMBUSH,
                    "lie in wait hidden here and pounce on smaller prey that comes close",
                    context.drives.hunger * organism.trait("patience"),
                )
            )
        return options

    def _entities(self, context: MindContext) -> list[Affordance]:
        organism = context.organism
        attention = self._attention_span(organism)
        options: list[Affordance] = []
        for percept in context.field.entities[:attention]:
            if percept.kind == EntityKind.CARCASS:
                options.extend(self._carcass_options(context, percept))
                continue
            target = context.animals(percept.target_id)
            if target is None or not target.alive:
                continue
            if target.species_id == organism.species_id:
                options.extend(self._conspecific_options(context, percept, target))
            else:
                options.extend(self._other_species_options(context, percept, target))
            options.extend(self._shared_animal_options(context, percept, target))
        return options

    def _attention_span(self, organism: Organism) -> int:
        cognition = self._ecology.cognition
        span = cognition.max_attention_entities - cognition.min_attention_entities
        return cognition.min_attention_entities + round(span * organism.trait("attention_span"))

    def _shared_animal_options(
        self, context: MindContext, percept: EntityPercept, target: Organism
    ) -> list[Affordance]:
        label = percept.label
        what = self._short(context, percept, target)
        options: list[Affordance] = []
        hostile = target.id in (context.organism.body.attacked_by, context.organism.social.last_defeated_by)
        if target.species_id != context.organism.species_id or percept.danger >= DANGEROUS or hostile:
            options.append(
                Affordance(
                    f"flee_from_{label}",
                    Verb.FLEE,
                    f"run away from {label} ({what}){self._escape_hint(context, percept)}",
                    percept.danger * self._weights.flee_danger + context.drives.fear,
                    target_kind=TargetKind.ANIMAL,
                    target_id=target.id,
                )
            )
        if context.organism.body.attacked_by == target.id and percept.touching:
            options.append(
                Affordance(
                    f"fight_back_{label}",
                    Verb.FIGHT_BACK,
                    f"fight back against {label}",
                    self._weights.fight_back_base + context.organism.trait("boldness"),
                    target_kind=TargetKind.ANIMAL,
                    target_id=target.id,
                )
            )
        if percept.distance <= DISPLAY_RANGE:
            options.append(
                Affordance(
                    f"threat_display_at_{label}",
                    Verb.THREAT_DISPLAY,
                    f"bare your teeth and puff up at {label} to scare it off",
                    percept.danger * context.organism.trait("boldness"),
                    target_kind=TargetKind.ANIMAL,
                    target_id=target.id,
                )
            )
        if target.body.carrying is not None and percept.touching:
            options.append(
                Affordance(
                    f"steal_food_from_{label}",
                    Verb.STEAL_FOOD,
                    f"snatch the food {label} is carrying",
                    context.drives.hunger
                    * (self._weights.steal_base + context.organism.phenotype.instincts.get("kleptoparasitism", 0.0)),
                    target_kind=TargetKind.ANIMAL,
                    target_id=target.id,
                )
            )
        return options

    def _other_species_options(
        self, context: MindContext, percept: EntityPercept, target: Organism
    ) -> list[Affordance]:
        organism = context.organism
        label = percept.label
        what = self._short(context, percept, target)
        hunger = context.drives.hunger
        predatory = organism.phenotype.diet.animal >= PREDATORY_DIET
        reach = self._mechanics.steps_for_effort(organism, ALL_OUT_EFFORT, context.tick) + 1
        prey_drive = hunger * organism.phenotype.diet.animal
        options = [
            Affordance(
                f"approach_{label}",
                Verb.APPROACH,
                f"go toward {label} ({what})",
                self._weights.curiosity_approach * organism.trait("curiosity")
                + self._weights.prey_approach * prey_drive,
                target_kind=TargetKind.ANIMAL,
                target_id=target.id,
            )
        ]
        if percept.certainty < UNCERTAIN_IDENTITY:
            options.append(
                Affordance(
                    f"investigate_{label}",
                    Verb.INVESTIGATE,
                    f"carefully get closer to {label} to see what it is",
                    organism.trait("curiosity") * self._weights.investigate,
                    target_kind=TargetKind.ANIMAL,
                    target_id=target.id,
                )
            )
        if percept.distance <= reach:
            advantage = self._relations_hint_attack(context, target)
            options.append(
                Affordance(
                    f"attack_{label}",
                    Verb.ATTACK,
                    f"attack {label} ({what}){advantage}",
                    prey_drive + self._weights.defensive_attack * organism.trait("aggression") * percept.danger,
                    target_kind=TargetKind.ANIMAL,
                    target_id=target.id,
                )
            )
        if predatory and percept.distance > ADJACENT:
            options.append(
                Affordance(
                    f"stalk_{label}",
                    Verb.STALK,
                    f"creep slowly and quietly toward {label}",
                    prey_drive * organism.trait("patience"),
                    target_kind=TargetKind.ANIMAL,
                    target_id=target.id,
                )
            )
            if percept.distance <= 2 * reach:
                options.append(
                    Affordance(
                        f"chase_{label}",
                        Verb.CHASE,
                        f"chase {label} at full speed",
                        prey_drive,
                        target_kind=TargetKind.ANIMAL,
                        target_id=target.id,
                    )
                )
        allies = sum(
            1
            for other in context.group
            if context.world.metric.distance(organism.position, other.position) <= ALLY_RANGE
        )
        if percept.touching and allies >= 1 and percept.danger > DANGEROUS:
            options.append(
                Affordance(
                    f"mob_{label}",
                    Verb.MOB,
                    f"harass {label} together with your kind",
                    percept.danger * organism.trait("boldness"),
                    target_kind=TargetKind.ANIMAL,
                    target_id=target.id,
                )
            )
        return options

    def _conspecific_options(self, context: MindContext, percept: EntityPercept, target: Organism) -> list[Affordance]:
        organism = context.organism
        label = percept.label
        what = self._short(context, percept, target)
        drives = context.drives
        kin = organism.lineage.relatedness(target.lineage)
        options = [
            Affordance(
                f"follow_{label}",
                Verb.FOLLOW,
                f"follow {label} ({what})",
                drives.social_need
                + self._weights.follow_kin * kin
                + (self._weights.follow_mother if self._is_nursing_mother(organism, target) else 0.0),
                target_kind=TargetKind.ANIMAL,
                target_id=target.id,
            )
        ]
        if percept.touching:
            options.append(
                Affordance(
                    f"groom_{label}",
                    Verb.GROOM,
                    f"groom {label}",
                    self._weights.groom_social * organism.trait("sociability") + target.body.parasite_load * kin,
                    target_kind=TargetKind.ANIMAL,
                    target_id=target.id,
                )
            )
            if target.id in organism.reproduction.dependents and organism.reproduction.lactating:
                options.append(
                    Affordance(
                        f"nurse_{label}",
                        Verb.NURSE,
                        f"let {label} suckle your milk",
                        self._weights.nurse_base + organism.trait("parental_care"),
                        target_kind=TargetKind.ANIMAL,
                        target_id=target.id,
                    )
                )
            if organism.body.carrying is not None:
                options.append(
                    Affordance(
                        f"share_food_with_{label}",
                        Verb.SHARE_FOOD,
                        f"give the food you carry to {label}",
                        organism.trait("altruism") * kin * self._weights.share_kin,
                        target_kind=TargetKind.ANIMAL,
                        target_id=target.id,
                    )
                )
        options.extend(self._mating_options(context, percept, target, what))
        if organism.is_adult and target.is_adult and target.reproduction.sex == organism.reproduction.sex:
            if percept.distance <= CHALLENGE_RANGE:
                options.append(
                    Affordance(
                        f"challenge_{label}",
                        Verb.CHALLENGE,
                        f"challenge {label} to settle who is dominant",
                        organism.trait("aggression")
                        * max(drives.urge_to_mate, drives.hunger)
                        * self._weights.challenge,
                        target_kind=TargetKind.ANIMAL,
                        target_id=target.id,
                    )
                )
            if percept.distance <= DISPLAY_RANGE:
                options.append(
                    Affordance(
                        f"submit_to_{label}",
                        Verb.SUBMIT,
                        f"back down and show {label} you will not fight",
                        drives.fear * self._weights.submit,
                        target_kind=TargetKind.ANIMAL,
                        target_id=target.id,
                    )
                )
        return options

    def _mating_options(
        self, context: MindContext, percept: EntityPercept, target: Organism, what: str
    ) -> list[Affordance]:
        organism = context.organism
        label = percept.label
        urge = context.drives.urge_to_mate
        options: list[Affordance] = []
        opposite = target.reproduction.sex != organism.reproduction.sex
        if not (opposite and context.mate_eligible(organism) and context.mate_eligible(target)):
            return options
        if percept.distance <= COURT_RANGE:
            options.append(
                Affordance(
                    f"court_{label}",
                    Verb.COURT,
                    f"court {label} with a display ({what})",
                    urge,
                    target_kind=TargetKind.ANIMAL,
                    target_id=target.id,
                )
            )
        memory = self._ecology.reproduction.courtship_memory_ticks
        courted_recently = context.tick - organism.reproduction.courted_by.get(target.id, -10_000) <= memory
        if courted_recently and percept.touching:
            options.append(
                Affordance(
                    f"mate_with_{label}",
                    Verb.MATE_WITH,
                    f"accept {label} and mate",
                    urge * self._weights.accept_mate,
                    target_kind=TargetKind.ANIMAL,
                    target_id=target.id,
                )
            )
        return options

    def _carcass_options(self, context: MindContext, percept: EntityPercept) -> list[Affordance]:
        organism = context.organism
        label = percept.label
        meat_weight = organism.phenotype.diet.animal
        if meat_weight < MIN_DIET_WEIGHT:
            return []
        hunger = context.drives.hunger
        if percept.touching:
            options = [
                Affordance(
                    f"eat_carcass_{label}",
                    Verb.EAT_CARCASS,
                    f"feed on the carcass {label}",
                    hunger * meat_weight * self._weights.carcass,
                    target_kind=TargetKind.CARCASS,
                    target_id=percept.target_id,
                )
            ]
            if organism.body.carrying is None:
                options.append(
                    Affordance(
                        f"carry_food_from_{label}",
                        Verb.CARRY_FOOD,
                        f"tear off meat from {label} and carry it",
                        self._weights.carry
                        * (
                            organism.phenotype.instincts.get("food_caching", 0.0)
                            + float(bool(organism.reproduction.dependents))
                        ),
                        target_kind=TargetKind.CARCASS,
                        target_id=percept.target_id,
                    )
                )
            return options
        return [
            Affordance(
                f"approach_{label}",
                Verb.APPROACH,
                f"go to the carcass {label}",
                hunger * meat_weight,
                target_kind=TargetKind.CARCASS,
                target_id=percept.target_id,
            )
        ]

    def _scents(self, context: MindContext) -> list[Affordance]:
        options: list[Affordance] = []
        for scent in context.field.scents[:SCENT_OPTIONS]:
            if scent.direction is None:
                continue
            dangerous = scent.channel in ("smoke", "blood", "alarm_pheromone") or (
                scent.species_id is not None
                and context.organism.memory.associations.value(f"species:{scent.species_id}") < -DANGEROUS
            )
            if dangerous:
                options.append(
                    Affordance(
                        f"flee_from_{scent.label}",
                        Verb.FLEE,
                        f"move away from the smell {scent.label} ({scent.direction.word})",
                        scent.salience,
                        target_kind=TargetKind.SCENT,
                        direction=scent.direction.opposite,
                    )
                )
            else:
                options.append(
                    Affordance(
                        f"follow_scent_{scent.label}",
                        Verb.FOLLOW_SCENT,
                        f"follow the smell {scent.label} toward the {scent.direction.word}",
                        scent.salience,
                        target_kind=TargetKind.SCENT,
                        direction=scent.direction,
                    )
                )
        return options

    def _sounds(self, context: MindContext) -> list[Affordance]:
        options: list[Affordance] = []
        for sound in context.field.sounds[:SOUND_OPTIONS]:
            if sound.event.kind in ALARMING_SOUNDS:
                options.append(
                    Affordance(
                        f"flee_from_{sound.label}",
                        Verb.FLEE,
                        f"move away from the sound {sound.label} ({sound.direction.word})",
                        sound.salience,
                        target_kind=TargetKind.SOUND,
                        direction=sound.direction.opposite,
                    )
                )
            options.append(
                Affordance(
                    f"investigate_{sound.label}",
                    Verb.INVESTIGATE,
                    f"go carefully toward the sound {sound.label} ({sound.direction.word})",
                    self._weights.investigate_sound * context.organism.trait("curiosity"),
                    target_kind=TargetKind.SOUND,
                    destination=sound.event.position,
                )
            )
        return options

    def _memories(self, context: MindContext) -> list[Affordance]:
        organism = context.organism
        drives = context.drives
        wanted: list[tuple[float, str, PlaceMemory]] = []
        for place in organism.memory.spatial.recall("", context.tick):
            need = self._memory_need(organism, place.kind, drives)
            if need > NEED_THRESHOLD and place.position != organism.position:
                wanted.append((need, place.kind, place))
        wanted.sort(key=_first, reverse=True)
        options: list[Affordance] = []
        for index, (need, kind, place) in enumerate(wanted[:MEMORY_OPTIONS], start=1):
            distance = context.world.metric.distance(organism.position, place.position)
            direction = context.world.metric.direction(organism.position, place.position)
            when = self._recency.word(context.tick - place.tick_seen)
            name = MEMORY_PHRASES.get(kind, "good food" if kind.startswith("food:") else kind)
            key_kind = kind.replace("food:", "food_")
            options.append(
                Affordance(
                    f"go_to_{key_kind}_memory_{index}",
                    Verb.GO_TO_MEMORY,
                    f"head for {name} you remember, {DISTANCE.word(distance)} to the {direction.word} (seen {when})",
                    need,
                    target_kind=TargetKind.MEMORY,
                    destination=place.position,
                )
            )
        return options

    def _memory_need(self, organism: Organism, kind: str, drives: DriveState) -> float:
        if kind == "water":
            return drives.thirst
        if kind == "den":
            return max(drives.sleepiness, drives.fear)
        if kind == "refuge":
            return drives.fear
        if kind == "meat":
            return drives.hunger * organism.phenotype.diet.animal
        layer = kind.removeprefix("food:")
        if kind.startswith("food:") and layer in self._ecology.food_layers:
            return drives.hunger * organism.phenotype.diet.weight(self._ecology.food_layers[layer].diet_class)
        return 0.0

    @staticmethod
    def _is_nursing_mother(organism: Organism, target: Organism) -> bool:
        return target.id == organism.reproduction.mother_id and not organism.reproduction.weaned

    def _group(self, context: MindContext) -> list[Affordance]:
        if len(context.group) < 2:
            return []
        adjacent = sum(
            1 for other in context.group if context.world.metric.are_adjacent(context.organism.position, other.position)
        )
        if adjacent >= len(context.group) // 2:
            return []
        return [
            Affordance(
                "stay_with_group",
                Verb.STAY_WITH_GROUP,
                "move closer to your group",
                context.drives.social_need
                + self._weights.herd * context.organism.phenotype.instincts.get("herd_cohesion", 0.0),
            )
        ]

    def _escape_hint(self, context: MindContext, percept: EntityPercept) -> str:
        world = context.world
        away = percept.direction.opposite
        step = world.metric.step(context.organism.position, away)
        terrain = world.terrain_at(step)
        if world.cover(step) >= HIDING_COVER:
            return f"; there is cover to the {away.word}"
        if terrain == TerrainType.DEEP_WATER and self._mechanics.can_swim_deep(context.organism):
            return f"; deep water to the {away.word} you can swim into"
        return ""

    def _relations_hint_attack(self, context: MindContext, target: Organism) -> str:
        noticed = context.noticed(target.id, context.organism.id)
        return "; it has not noticed you" if not noticed else ""

    def _short(self, context: MindContext, percept: EntityPercept, target: Organism) -> str:
        kin = self._relations.kinship(context.organism, target)
        if kin is not None:
            return kin
        if percept.certainty < UNCLEAR_SHAPE_CERTAINTY:
            return "an unclear shape"
        size = self._relations.size_phrase(context.organism, target)
        if target.species_id == context.organism.species_id:
            return f"one of your kind, {size}"
        return f"{context.species_name(target.species_id)}, {size}"


def _relevance(affordance: Affordance) -> float:
    return affordance.relevance


def _first(entry: tuple[float, str, PlaceMemory]) -> float:
    return entry[0]
