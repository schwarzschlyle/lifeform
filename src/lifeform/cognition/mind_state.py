from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

from lifeform.actions.calls import CALL_SPECS, Call
from lifeform.actions.verbs import VERB_SPECS, Verb
from lifeform.biology.drives import Condition
from lifeform.biology.instincts import INSTINCT_BY_KEY
from lifeform.biology.mechanics import BodyMechanics
from lifeform.biology.organism import Organism
from lifeform.biology.phenotype import DietProfile
from lifeform.cognition.context import MindContext
from lifeform.cognition.relations import RelationalFacts
from lifeform.cognition.vocabulary import (
    COVER,
    DISTANCE,
    FEAR,
    FOOD_AMOUNT,
    HEALTH,
    HUNGER,
    INSTINCT_STRENGTH,
    LOUDNESS,
    PAIN,
    SCENT_INTENSITY,
    SLEEPINESS,
    SNOW,
    TEMPERAMENT_WORDS,
    THERMAL,
    THIRST,
    URGE_TO_MATE,
    RecencyWords,
    activity_word,
    temperament_word,
)
from lifeform.config.parameters import CognitionParameters, EcologyParameters
from lifeform.perception.percepts import EntityKind, ScentPercept, SoundPercept
from lifeform.world.climate import WeatherState
from lifeform.world.fields import ScentLandscape
from lifeform.world.terrain import TERRAIN, FoodLayer

TASK = "This is one wild animal's experience of this moment. 'You' means this animal."
CHARACTERS_PER_TOKEN = 4.0
MAX_INSTINCTS = 5
DIET_NOTABLE = 0.2
DIET_INDIGESTIBLE = 0.08
SOCIAL_NEED_NOTABLE = 0.3
MATE_URGE_NOTABLE = 0.05
TINY_KG = 1.0
SMALL_KG = 10.0
MEDIUM_KG = 60.0
LARGE_KG = 200.0
INSECT_EATER_KG = 3.0
OMNIVORE_BALANCE = 0.3
FAST_LIMBS = 0.65
SLOW_LIMBS = 0.35
ARMORED = 0.6
THICK_FUR = 0.6
HORNS = 0.3
BIG_WEAPONS = 0.6
EPISODES_SHOWN = 2
YOUNG_ADULT_MATURITY_MULTIPLE = 1.5
LATE_PREGNANCY = 0.66
DISPLAY_ORNAMENT_WEIGHT = 0.4
DISPLAY_HEALTH_WEIGHT = 0.3
DISPLAY_ENERGY_WEIGHT = 0.3
DISPLAY_TIERS: tuple[tuple[float, str], ...] = (
    (0.75, "a vivid, vigorous, impressive display"),
    (0.5, "a confident display"),
    (0.3, "a modest display"),
)
DULL_DISPLAY = "a dull, half-hearted display"
NOTABLE_SNOW_CM = 5.0
NOTABLE_TOXIN = 0.1
BROWSER_PREFERENCE = 0.5

WEATHER_WORDS: dict[WeatherState, str] = {
    WeatherState.CLEAR: "clear sky",
    WeatherState.CLOUDY: "cloudy",
    WeatherState.FOG: "foggy",
    WeatherState.RAIN: "raining",
    WeatherState.STORM: "a storm with strong wind",
}
SCENT_WORDS: dict[str, str] = {
    "fruit_aroma": "ripe fruit",
    "carrion": "rotting meat",
    "blood": "fresh blood",
    "water": "water",
    "smoke": "smoke",
    "alarm_pheromone": "the fear-scent of an injured animal",
}
NOISE_WORDS: dict[str, str] = {
    "footsteps": "running footsteps",
    "fight": "the sounds of a fight",
    "scream": "a death scream",
    "splash": "a splash",
    "crash": "a crash",
}
CONDITION_PHRASES: dict[Condition, str] = {
    Condition.ASLEEP: "you are asleep",
    Condition.HIDDEN: "you are hidden",
    Condition.IN_DEN: "you are inside a den",
    Condition.CLIMBING: "you are up in a tree",
    Condition.SWIMMING: "you are swimming",
    Condition.LACTATING: "you are nursing young",
    Condition.IN_ESTRUS: "you are in heat",
    Condition.BLEEDING: "you are bleeding",
    Condition.LIMPING: "you are limping",
    Condition.POISONED: "you feel poisoned",
    Condition.INFECTED_SICK: "you feel sick and feverish",
    Condition.EXHAUSTED: "you are out of breath and exhausted",
    Condition.DEHYDRATED: "you are badly dehydrated",
    Condition.STARVING: "you are starving and wasting away",
    Condition.CARRYING_FOOD: "you are carrying food in your mouth",
    Condition.BEING_CHASED: "you are being chased",
    Condition.RECENTLY_DEFEATED: "you recently lost a fight for dominance",
}


@dataclass(frozen=True, slots=True)
class MindState:
    organism_id: int
    payload: dict[str, Any]
    focus_options: dict[str, str]

    def to_json(self) -> str:
        return json.dumps(self.payload, ensure_ascii=False)

    @property
    def estimated_tokens(self) -> int:
        return int(len(self.to_json()) / CHARACTERS_PER_TOKEN)


class MindStateEncoder:
    def __init__(
        self, ecology: EcologyParameters, mechanics: BodyMechanics, relations: RelationalFacts, recency: RecencyWords
    ) -> None:
        self._ecology = ecology
        self._cognition: CognitionParameters = ecology.cognition
        self._mechanics = mechanics
        self._relations = relations
        self._recency = recency

    def encode(self, context: MindContext) -> MindState:
        focus: dict[str, str] = {}
        payload: dict[str, Any] = {
            "task": TASK,
            "you": self._you(context),
            "feelings": self._feelings(context),
            "time": self._time(context),
            "here": self._here(context),
        }
        conditions = self._conditions(context)
        if conditions:
            payload["conditions"] = conditions
        around = self._around(context, focus)
        payload["around_you"] = around if around else ["nothing you can see or touch"]
        smells = self._smells(context, focus)
        if smells:
            payload["smells"] = smells
        sounds = self._sounds(context, focus)
        if sounds:
            payload["sounds"] = sounds
        memories = self._memories(context)
        if memories:
            payload["memories"] = memories
        payload["recent"] = self._recent(context)
        state = MindState(context.organism.id, payload, focus)
        return self._trimmed(state, context)

    def _trimmed(self, state: MindState, context: MindContext) -> MindState:
        payload = state.payload
        while state.estimated_tokens > self._cognition.max_state_tokens:
            for key in ("around_you", "memories", "smells", "sounds"):
                items = payload.get(key)
                if isinstance(items, list) and len(items) > 1:
                    removed = items.pop()
                    if isinstance(removed, dict):
                        state.focus_options.pop(str(removed.get("id")), None)
                    break
            else:
                break
            state = MindState(context.organism.id, payload, state.focus_options)
        return state

    def _you(self, context: MindContext) -> dict[str, Any]:
        organism = context.organism
        you: dict[str, Any] = {
            "kind": self._kind(context),
            "body": self._body(organism),
            "diet": self._diet(organism.phenotype.diet),
            "rhythm": activity_word(organism.phenotype.activity_phase),
        }
        temperament = self._temperament(organism)
        if temperament:
            you["temperament"] = temperament
        instincts = self._instincts(organism)
        if instincts:
            you["instincts"] = instincts
        return you

    def _kind(self, context: MindContext) -> str:
        organism = context.organism
        mass = organism.body.mass_kg
        size = (
            "a tiny"
            if mass < TINY_KG
            else "a small"
            if mass < SMALL_KG
            else "a medium-sized"
            if mass < MEDIUM_KG
            else "a large"
            if mass < LARGE_KG
            else "a very large"
        )
        diet = organism.phenotype.diet
        eater = self._eater_word(diet, organism.phenotype.adult_mass_kg)
        species = context.species_name(organism.species_id)
        return f"{size} {eater} of the {species} kind, {organism.reproduction.sex.value}, {self._life_stage(organism)}"

    @staticmethod
    def _eater_word(diet: DietProfile, adult_mass: float) -> str:
        if diet.animal >= 0.5:
            return "insect-eater" if adult_mass < INSECT_EATER_KG else "meat-eater"
        if diet.animal >= OMNIVORE_BALANCE:
            return "omnivore"
        return "plant-eater"

    def _life_stage(self, organism: Organism) -> str:
        if not organism.reproduction.weaned:
            return "a newborn" if self._mechanics.is_immobile_newborn(organism) else "a suckling youngster"
        if not organism.reproduction.mature:
            return "a juvenile"
        if self._mechanics.is_senescent(organism):
            return "old"
        young_adult = organism.body.age_ticks < YOUNG_ADULT_MATURITY_MULTIPLE * organism.phenotype.maturity_ticks
        return "a young adult" if young_adult else "an adult"

    @staticmethod
    def _body(organism: Organism) -> str:
        parts: list[str] = []
        limbs = organism.trait("limb_ratio")
        parts.append(
            "long-legged and quick"
            if limbs > FAST_LIMBS
            else ("short-legged and slow" if limbs < SLOW_LIMBS else "sturdy legs")
        )
        weapons = organism.trait("weaponry")
        if organism.phenotype.diet.animal >= 0.5:
            parts.append("big fangs and claws" if weapons > BIG_WEAPONS else "sharp teeth")
        elif weapons > HORNS:
            parts.append("strong horns" if weapons > BIG_WEAPONS else "small horns")
        else:
            parts.append("blunt teeth")
        if organism.trait("armor") > ARMORED:
            parts.append("a tough armored hide")
        if organism.trait("insulation") > THICK_FUR:
            parts.append("thick fur")
        if organism.trait("toxicity") > ARMORED:
            parts.append("foul-tasting, toxic flesh")
        if organism.trait("swim_skill") > FAST_LIMBS:
            parts.append("a strong swimmer")
        if organism.trait("climb_skill") > FAST_LIMBS:
            parts.append("a good climber")
        if organism.trait("dig_skill") > FAST_LIMBS:
            parts.append("a strong digger")
        return "; ".join(parts)

    @staticmethod
    def _diet(diet: DietProfile) -> str:
        foods: list[str] = []
        if diet.fiber >= DIET_NOTABLE:
            foods.append("grass" if diet.grazer_browser < BROWSER_PREFERENCE else "leaves and twigs")
        if diet.soft >= DIET_NOTABLE:
            foods.append("fruit, seeds and soft plants")
        if diet.animal >= DIET_NOTABLE:
            foods.append("meat, insects and grubs")
        cannot = [
            name
            for name, weight in (("tough plants", diet.fiber), ("fruit and seeds", diet.soft), ("meat", diet.animal))
            if weight < DIET_INDIGESTIBLE
        ]
        eats = f"eats {', '.join(foods)}" if foods else "eats a little of everything"
        return f"{eats}; cannot digest {' or '.join(cannot)}" if cannot else eats

    @staticmethod
    def _temperament(organism: Organism) -> str:
        words = [
            word for trait in TEMPERAMENT_WORDS if (word := temperament_word(trait, organism.trait(trait))) is not None
        ]
        return ", ".join(words)

    @staticmethod
    def _instincts(organism: Organism) -> list[str]:
        ranked = sorted(organism.phenotype.instincts.items(), key=_strength, reverse=True)[:MAX_INSTINCTS]
        return [f"{INSTINCT_STRENGTH.word(value)} {INSTINCT_BY_KEY[key].wording}" for key, value in ranked]

    def _feelings(self, context: MindContext) -> dict[str, str]:
        drives = context.drives
        organism = context.organism
        feelings = {
            "hunger": HUNGER.word(drives.hunger),
            "thirst": THIRST.word(drives.thirst),
            "tiredness": SLEEPINESS.word(drives.sleepiness),
            "temperature": THERMAL.word(drives.thermal),
            "health": HEALTH.word(organism.body.health),
            "pain": PAIN.word(drives.pain),
            "fear": FEAR.word(drives.fear),
        }
        if drives.urge_to_mate > MATE_URGE_NOTABLE:
            feelings["urge_to_mate"] = URGE_TO_MATE.word(drives.urge_to_mate)
        if drives.social_need > SOCIAL_NEED_NOTABLE:
            feelings["company"] = "lonely; you miss others of your kind"
        if drives.parental_urge > 0.0:
            feelings["young"] = "your young are out of sight"
        if drives.exploratory_urge > SOCIAL_NEED_NOTABLE:
            feelings["restlessness"] = "restless to explore somewhere new"
        return feelings

    def _conditions(self, context: MindContext) -> list[str]:
        organism = context.organism
        phrases = [phrase for flag, phrase in CONDITION_PHRASES.items() if flag in context.conditions]
        pregnancy = organism.reproduction.pregnancy
        if pregnancy is not None:
            stage = "late in pregnancy" if pregnancy.progress(context.tick) > LATE_PREGNANCY else "pregnant"
            phrases.append(f"you are {stage}")
        for suitor_id in organism.reproduction.courted_by:
            suitor = context.animals(suitor_id)
            label = self._label_of(context, suitor_id)
            if suitor is not None and label is not None:
                phrases.append(f"{label} is courting you with {self._display_words(suitor)}")
        return phrases

    def _display_words(self, suitor: Organism) -> str:
        quality = (
            DISPLAY_ORNAMENT_WEIGHT * suitor.trait("ornament")
            + DISPLAY_HEALTH_WEIGHT * suitor.body.health
            + DISPLAY_ENERGY_WEIGHT * min(1.0, self._mechanics.energy_fraction(suitor))
        )
        for threshold, words in DISPLAY_TIERS:
            if quality > threshold:
                return words
        return DULL_DISPLAY

    def _time(self, context: MindContext) -> str:
        calendar = context.world.calendar
        weather = context.world.climate_state
        snowing = weather.raining and context.world.temperature(context.organism.position) < 0.0
        sky = "snowing" if snowing else WEATHER_WORDS[weather.weather]
        if context.world.preset.climate.tidally_locked:
            return f"the endless twilight, {sky}"
        return f"{calendar.day_phase_word(context.tick)}, {calendar.season_word(context.tick)}, {sky}"

    def _here(self, context: MindContext) -> str:
        organism = context.organism
        world = context.world
        position = organism.position
        parts = [TERRAIN.description(world.terrain_at(position))]
        snow = float(world.fields.hydrology.snow_depth[position.y, position.x])
        bite = self._mechanics.bite_capacity(organism)
        for layer in FoodLayer:
            parameters = self._ecology.food_layers[layer.key]
            if organism.phenotype.diet.weight(parameters.diet_class) < DIET_INDIGESTIBLE:
                continue
            amount = world.fields.vegetation.accessible(layer, position.x, position.y, snow)
            if amount > 0.0 and world.fields.vegetation.capacity[layer, position.y, position.x] > 0.0:
                parts.append(f"{layer.key} here: {FOOD_AMOUNT.word(amount / max(bite, 1e-6))}")
        parts.append("water beside you" if world.drinkable_near(position) is not None else "no water here")
        parts.append(COVER.word(world.cover(position)))
        if snow > NOTABLE_SNOW_CM:
            parts.append(SNOW.word(snow))
        if float(world.fields.toxin.level[position.y, position.x]) > NOTABLE_TOXIN:
            parts.append("the ground here smells toxic")
        if any(world.is_burning(neighbor) for neighbor in world.metric.neighbors(position)):
            parts.append("fire is burning right next to you")
        den = world.dens.at(position)
        if den is not None and den.owner_id == organism.id:
            parts.append("your den is here")
        return "; ".join(parts)

    def _around(self, context: MindContext, focus: dict[str, str]) -> list[dict[str, str]]:
        span = self._cognition.max_attention_entities - self._cognition.min_attention_entities
        limit = self._cognition.min_attention_entities + round(span * context.organism.trait("attention_span"))
        described: list[dict[str, str]] = []
        for percept in context.field.entities[:limit]:
            if percept.kind == EntityKind.CARCASS:
                carcass = context.carcasses(percept.target_id)
                if carcass is None:
                    continue
                description = self._relations.describe_carcass(context, percept, carcass)
            else:
                target = context.animals(percept.target_id)
                if target is None:
                    continue
                description = self._relations.describe_animal(context, percept, target)
            focus[percept.label] = description["what"]
            described.append(description)
        return described

    def _smells(self, context: MindContext, focus: dict[str, str]) -> list[str]:
        phrases: list[str] = []
        for scent in context.field.scents[: self._cognition.max_smells]:
            phrase = self._smell_phrase(context, scent)
            focus[scent.label] = phrase.split(",")[0]
            phrases.append(f"{scent.label}: {phrase}")
        return phrases

    def _smell_phrase(self, context: MindContext, scent: ScentPercept) -> str:
        if scent.channel.startswith(ScentLandscape.ESTRUS_PREFIX):
            what = "a female of your kind ready to mate"
        elif scent.channel.startswith(ScentLandscape.MUSK_PREFIX) and scent.species_id is not None:
            what = (
                "the scent of your own kind"
                if scent.species_id == context.organism.species_id
                else f"the scent of a {context.species_name(scent.species_id)}"
            )
        else:
            what = SCENT_WORDS.get(scent.channel, scent.channel)
        where = f"from the {scent.direction.word}" if scent.direction is not None else "right here"
        wind = ", carried on the wind" if scent.upwind else ""
        return f"{what}, {SCENT_INTENSITY.word(scent.intensity)}, {where}{wind}"

    def _sounds(self, context: MindContext, focus: dict[str, str]) -> list[str]:
        phrases: list[str] = []
        for sound in context.field.sounds[: self._cognition.max_sounds]:
            phrase = self._sound_phrase(context, sound)
            focus[sound.label] = phrase.split(",")[0]
            phrases.append(f"{sound.label}: {phrase}")
        return phrases

    def _sound_phrase(self, context: MindContext, sound: SoundPercept) -> str:
        event = sound.event
        if event.is_call:
            spec = CALL_SPECS[Call(event.kind)]
            source = "your kind" if event.species_id == context.organism.species_id else "another kind of animal"
            what = f"{spec.heard_as} from {source}"
        else:
            what = NOISE_WORDS.get(event.kind, "a noise")
        return f"{what}, {LOUDNESS.word(sound.loudness_db)}, from the {sound.direction.word}, just now"

    def _memories(self, context: MindContext) -> list[str]:
        organism = context.organism
        tick = context.tick
        phrases: list[str] = []
        for place in organism.memory.spatial.strongest(self._cognition.max_memories, tick):
            distance = context.world.metric.distance(organism.position, place.position)
            direction = context.world.metric.direction(organism.position, place.position)
            where = "right here" if distance < 1.0 else f"{DISTANCE.word(distance)} to the {direction.word}"
            kind = place.kind.replace("food:", "good ").replace("_", " ")
            phrases.append(f"{kind}: {where} (seen {self._recency.word(tick - place.tick_seen)})")
        recent_episodes = list(organism.memory.episodic.episodes)[-EPISODES_SHOWN:]
        phrases.extend(f"{self._recency.word(tick - episode.tick)}, {episode.text}" for episode in recent_episodes)
        return phrases

    def _recent(self, context: MindContext) -> list[str]:
        recent = [VERB_SPECS[Verb(verb)].past_tense for verb in context.organism.body.last_actions]
        if context.last_outcome:
            recent.append(context.last_outcome)
        return recent or ["just arrived here"]

    @staticmethod
    def _label_of(context: MindContext, organism_id: int) -> str | None:
        for percept in context.field.entities:
            if percept.target_id == organism_id and percept.kind == EntityKind.ANIMAL:
                return percept.label
        return None


def _strength(item: tuple[str, float]) -> float:
    return item[1]
