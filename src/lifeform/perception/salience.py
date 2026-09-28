from __future__ import annotations

import math
from collections.abc import Callable

from lifeform.biology.drives import DriveState
from lifeform.biology.mechanics import BodyMechanics
from lifeform.biology.organism import Organism
from lifeform.config.parameters import CognitionParameters
from lifeform.perception.percepts import EntityKind, EntityPercept, PerceptualField, ScentPercept, SoundPercept
from lifeform.world.entities import Carcass
from lifeform.world.fields import ScentLandscape

ALL_OUT_EFFORT = 3
DANGER_SLOPE = 1.5
PREY_SIZE_PREFERENCE = 2.0
CONSPECIFIC_DANGER = 0.1
DANGEROUS_SCENTS: dict[str, float] = {"smoke": 1.0, "blood": 0.3, "alarm_pheromone": 0.6}
ALARMING_CALLS: dict[str, float] = {"alarm_call": 0.8, "distress_call": 0.5, "warning_growl": 0.6}
NOISE_DANGER: dict[str, float] = {"fight": 0.5, "scream": 0.5, "footsteps": 0.2, "crash": 0.3}
UNKNOWN_NOISE_DANGER = 0.2
BASE_RELEVANCE = 0.2
FAMILY_BASELINE_NEED = 0.5
GROUP_NEED_WEIGHT = 0.5


def _sigmoid(value: float) -> float:
    return 1.0 / (1.0 + math.exp(-value))


class DangerAssessor:
    def __init__(self, mechanics: BodyMechanics) -> None:
        self._mechanics = mechanics

    def danger(self, viewer: Organism, target: Organism) -> float:
        if target.species_id == viewer.species_id:
            return CONSPECIFIC_DANGER * target.trait("aggression") if target.is_adult else 0.0
        ratio = self._mechanics.attack_power(target, ALL_OUT_EFFORT) / max(self._mechanics.defense(viewer), 1e-6)
        morphological = target.phenotype.diet.animal * _sigmoid(DANGER_SLOPE * math.log(max(ratio, 1e-6)))
        learned = max(0.0, -viewer.memory.associations.value(f"species:{target.species_id}"))
        return min(1.0, max(morphological, learned))

    def prey_value(self, viewer: Organism, target: Organism) -> float:
        if target.species_id == viewer.species_id:
            return 0.0
        size_fit = _sigmoid(math.log(PREY_SIZE_PREFERENCE * viewer.body.mass_kg / max(target.body.mass_kg, 1e-6)))
        learned = viewer.memory.associations.value(f"species:{target.species_id}")
        return viewer.phenotype.diet.animal * size_fit * (1.0 + min(0.0, learned))


class SalienceRanker:
    def __init__(self, parameters: CognitionParameters, assessor: DangerAssessor) -> None:
        self._parameters = parameters
        self._assessor = assessor

    def rank(
        self,
        viewer: Organism,
        field: PerceptualField,
        drives: DriveState,
        animals: Callable[[int], Organism | None],
        carcasses: Callable[[int], Carcass | None],
    ) -> None:
        for percept in field.entities:
            percept.salience, percept.danger = self._entity_salience(viewer, percept, drives, animals, carcasses)
        for scent in field.scents:
            scent.salience = self._scent_salience(viewer, scent, drives)
        for sound in field.sounds:
            sound.salience = self._sound_salience(viewer, sound, drives)
        field.entities.sort(key=_salience, reverse=True)
        field.scents.sort(key=_salience, reverse=True)
        field.sounds.sort(key=_salience, reverse=True)
        for index, percept in enumerate(field.entities, start=1):
            percept.label = f"P{index}"
        for index, scent in enumerate(field.scents, start=1):
            scent.label = f"S{index}"
        for index, sound in enumerate(field.sounds, start=1):
            sound.label = f"H{index}"

    def _entity_salience(
        self,
        viewer: Organism,
        percept: EntityPercept,
        drives: DriveState,
        animals: Callable[[int], Organism | None],
        carcasses: Callable[[int], Carcass | None],
    ) -> tuple[float, float]:
        parameters = self._parameters
        proximity = parameters.salience_distance_weight / (1.0 + percept.distance)
        if percept.kind == EntityKind.CARCASS:
            carcass = carcasses(percept.target_id)
            edible = viewer.phenotype.diet.animal if carcass is not None else 0.0
            return proximity + parameters.salience_need_weight * drives.hunger * edible, 0.0
        target = animals(percept.target_id)
        if target is None:
            return proximity, 0.0
        danger = self._assessor.danger(viewer, target)
        need = self._need(viewer, target, drives)
        kin = viewer.lineage.relatedness(target.lineage)
        novelty = viewer.memory.associations.novelty(f"species:{target.species_id}")
        approaching = percept.moving and target.body.heading == percept.direction.opposite
        salience = (
            proximity
            + parameters.salience_danger_weight * danger
            + parameters.salience_need_weight * need
            + parameters.salience_kin_weight * kin
            + parameters.salience_novelty_weight * novelty
            + parameters.salience_approach_weight * float(approaching)
        )
        return salience, danger

    def _need(self, viewer: Organism, target: Organism, drives: DriveState) -> float:
        if target.species_id != viewer.species_id:
            return drives.hunger * self._assessor.prey_value(viewer, target)
        dependents = viewer.reproduction.dependents
        if target.id in dependents or target.id == viewer.reproduction.mother_id:
            return max(drives.parental_urge, FAMILY_BASELINE_NEED)
        opposite_sex = target.reproduction.sex != viewer.reproduction.sex
        mate = drives.urge_to_mate if (opposite_sex and target.is_adult) else 0.0
        return max(mate, drives.social_need * GROUP_NEED_WEIGHT)

    def _scent_salience(self, viewer: Organism, scent: ScentPercept, drives: DriveState) -> float:
        diet = viewer.phenotype.diet
        strength = math.log1p(scent.intensity)
        relevance = DANGEROUS_SCENTS.get(scent.channel, 0.0)
        if scent.channel == "carrion":
            relevance = drives.hunger * diet.animal
        elif scent.channel == "fruit_aroma":
            relevance = drives.hunger * diet.soft
        elif scent.channel == "water":
            relevance = drives.thirst
        elif scent.channel.startswith(ScentLandscape.ESTRUS_PREFIX):
            relevance = drives.urge_to_mate
        elif scent.channel.startswith(ScentLandscape.MUSK_PREFIX) and scent.species_id is not None:
            association = viewer.memory.associations.value(f"species:{scent.species_id}")
            own_kind = scent.species_id == viewer.species_id
            relevance = drives.social_need if own_kind else abs(association)
        return strength * (BASE_RELEVANCE + relevance)

    def _sound_salience(self, viewer: Organism, sound: SoundPercept, drives: DriveState) -> float:
        kind = sound.event.kind
        own_kind = sound.event.species_id == viewer.species_id
        relevance = ALARMING_CALLS.get(kind, 0.0) if own_kind else NOISE_DANGER.get(kind, UNKNOWN_NOISE_DANGER)
        if kind == "mating_call" and own_kind:
            relevance = drives.urge_to_mate
        if kind == "contact_call" and own_kind:
            relevance = max(drives.social_need, drives.parental_urge)
        return math.log1p(max(sound.loudness_db, 0.0)) * (BASE_RELEVANCE + relevance)


def _salience(percept: EntityPercept | ScentPercept | SoundPercept) -> float:
    return percept.salience
