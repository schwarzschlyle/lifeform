from __future__ import annotations

from lifeform.biology.organism import Organism
from lifeform.perception.percepts import EntityKind
from lifeform.simulation.context import OrganismTickRecord, TickContext

INJURY_OUTCOME = -1.0
THREAT_OUTCOME = -0.5
MEAL_OUTCOME = 0.5
HARMLESS_OUTCOME = 0.0
HARMLESS_SALIENCE = 0.1
DANGER_MEMORY_QUALITY = 1.0
REFUGE_MEMORY_QUALITY = 0.8
POISONED_MEAL_TOXIN = 0.5
AFRAID = 0.3


class LearningPhase:
    name = "learning"

    def run(self, context: TickContext) -> None:
        focus_multiplier = context.services.ecology.memory.focus_learning_multiplier
        for organism in context.population.living():
            record = context.record(organism.id)
            focus_species = self._focus_species(context, organism)
            harmed_by = self._learn_from_harm(context, organism, record, focus_species, focus_multiplier)
            self._learn_from_meals(context, organism, record, focus_species, focus_multiplier)
            self._habituate(context, organism, harmed_by)
            self._remember_refuge(context, organism, record)
            context.persistent.last_outcomes[organism.id] = record.outcome or ""
            if not context.persistent.last_outcomes[organism.id]:
                context.persistent.last_outcomes.pop(organism.id)

    @staticmethod
    def _focus_species(context: TickContext, organism: Organism) -> int | None:
        intent = context.intents.get(organism.id)
        field = context.fields.get(organism.id)
        if intent is None or intent.focus_label is None or field is None:
            return None
        percept = field.entity(intent.focus_label)
        if percept is None or percept.kind != EntityKind.ANIMAL:
            return None
        target = context.population.any(percept.target_id)
        return target.species_id if target is not None else None

    @staticmethod
    def _salience(species_id: int, focus_species: int | None, multiplier: float) -> float:
        return multiplier if species_id == focus_species else 1.0

    def _learn_from_harm(
        self,
        context: TickContext,
        organism: Organism,
        record: OrganismTickRecord,
        focus_species: int | None,
        multiplier: float,
    ) -> set[int]:
        harmed_by: set[int] = set()
        memory = organism.memory
        for attacker_id in record.struck_by:
            attacker = context.population.any(attacker_id)
            if attacker is None:
                continue
            harmed_by.add(attacker.species_id)
            if attacker.species_id != organism.species_id:
                memory.associations.learn(
                    f"species:{attacker.species_id}",
                    INJURY_OUTCOME,
                    self._salience(attacker.species_id, focus_species, multiplier),
                )
            memory.social.note(attacker.id, attacker.species_id, "attacker", INJURY_OUTCOME, context.tick)
            memory.spatial.remember("danger", organism.position, DANGER_MEMORY_QUALITY, context.tick)
            memory.episodic.record(
                context.tick,
                f"you were attacked by {attacker.identity.name}, "
                f"a {context.services.species.name_of(attacker.species_id)}",
            )
        chaser = context.population.get(organism.body.chased_by)
        if chaser is not None and chaser.species_id != organism.species_id and chaser.species_id not in harmed_by:
            memory.associations.learn(
                f"species:{chaser.species_id}",
                THREAT_OUTCOME,
                self._salience(chaser.species_id, focus_species, multiplier),
            )
            harmed_by.add(chaser.species_id)
        return harmed_by

    def _learn_from_meals(
        self,
        context: TickContext,
        organism: Organism,
        record: OrganismTickRecord,
        focus_species: int | None,
        multiplier: float,
    ) -> None:
        if record.ate_meat_of is not None and record.ate_meat_of >= 0 and record.ate_meat_of != organism.species_id:
            outcome = INJURY_OUTCOME if organism.body.toxin_load > POISONED_MEAL_TOXIN else MEAL_OUTCOME
            organism.memory.associations.learn(
                f"species:{record.ate_meat_of}", outcome, self._salience(record.ate_meat_of, focus_species, multiplier)
            )
        for victim_id in record.struck:
            victim = context.population.any(victim_id)
            killed = victim is not None and victim.body.health <= 0.0
            if killed and victim is not None and victim.species_id != organism.species_id:
                organism.memory.associations.learn(f"species:{victim.species_id}", MEAL_OUTCOME)
                organism.memory.episodic.record(context.tick, f"you killed {victim.identity.name}")

    @staticmethod
    def _habituate(context: TickContext, organism: Organism, harmed_by: set[int]) -> None:
        field = context.fields.get(organism.id)
        if field is None:
            return
        for percept in field.entities:
            target = context.population.any(percept.target_id) if percept.kind == EntityKind.ANIMAL else None
            if target is None or target.species_id in harmed_by or target.species_id == organism.species_id:
                continue
            organism.memory.associations.learn(f"species:{target.species_id}", HARMLESS_OUTCOME, HARMLESS_SALIENCE)

    @staticmethod
    def _remember_refuge(context: TickContext, organism: Organism, record: OrganismTickRecord) -> None:
        safe = organism.body.hidden or organism.body.in_den or organism.body.climbing
        if safe and organism.body.fear > AFRAID and not record.struck_by:
            organism.memory.spatial.remember("refuge", organism.position, REFUGE_MEMORY_QUALITY, context.tick)
