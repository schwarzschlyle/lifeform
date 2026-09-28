from __future__ import annotations

from lifeform.biology.organism import Organism
from lifeform.core.events import EventKind
from lifeform.ecology.mortality import DeathCause
from lifeform.simulation.context import TickContext
from lifeform.world.acoustics import SoundEvent

SCREAM_DB = 85.0
NO_CARCASS_CAUSES = frozenset({DeathCause.DISASTER})


class LifecyclePhase:
    name = "lifecycle"

    def run(self, context: TickContext) -> None:
        for organism in context.population.living():
            self._housekeeping(context, organism)
            self._development(context, organism)
        newborns: list[Organism] = []
        for organism in context.population.living():
            newborns.extend(self._gestation(context, organism))
        for organism in context.population.living():
            cause = context.services.mortality.judge(organism, context.world)
            if cause is not None:
                self._die(context, organism, cause)
        for newborn in newborns:
            context.population.add(newborn)
            context.born.append(newborn.id)
        context.population.reindex()

    def _gestation(self, context: TickContext, mother: Organism) -> list[Organism]:
        pregnancy = mother.reproduction.pregnancy
        conception = context.services.conception
        if pregnancy is None:
            return []
        if conception.miscarries(mother):
            mother.reproduction.pregnancy = None
            context.emit(EventKind.MISCARRIAGE, (mother.id,), mother.position)
            return []
        if context.tick < pregnancy.due_tick:
            return []
        complicated = conception.birth_complication(mother)
        father = context.population.any(pregnancy.father_id)
        father_lineage = father.lineage if father is not None else mother.lineage
        birth_mass = pregnancy.litter_mass_kg / max(1, pregnancy.litter_size)
        newborns = [
            context.services.factory.offspring(
                mother, pregnancy.father_genome, father_lineage, birth_mass, context.tick
            )
            for _ in range(pregnancy.litter_size)
        ]
        mother.reproduction.pregnancy = None
        mother.reproduction.lactating = True
        mother.reproduction.offspring_count += len(newborns)
        mother.body.mass_kg = max(mother.body.lean_mass_kg, mother.body.mass_kg)
        for newborn in newborns:
            mother.reproduction.dependents.add(newborn.id)
            context.emit(
                EventKind.BIRTH,
                (newborn.id, mother.id, pregnancy.father_id),
                mother.position,
                species=newborn.species_id,
            )
        mother.memory.episodic.record(context.tick, f"you gave birth to {len(newborns)} young")
        if complicated:
            mother.body.take_damage("birth_complications", mother.body.health, context.tick)
        return newborns

    def _development(self, context: TickContext, organism: Organism) -> None:
        reproduction = organism.reproduction
        phenotype = organism.phenotype
        age = organism.body.age_ticks
        if not reproduction.weaned and age >= phenotype.weaning_ticks:
            reproduction.weaned = True
            mother = context.population.get(reproduction.mother_id)
            if mother is not None:
                mother.reproduction.dependents.discard(organism.id)
                organism.memory.inherit_from(
                    mother.memory, context.services.ecology.memory.inherited_memories, context.tick
                )
            context.emit(EventKind.WEANING, (organism.id,), organism.position)
        grown = organism.body.lean_mass_kg >= (
            context.services.ecology.life_history.adult_mass_fraction_for_maturity * phenotype.adult_mass_kg
        )
        if not reproduction.mature and reproduction.weaned and age >= phenotype.maturity_ticks and grown:
            reproduction.mature = True
            context.emit(EventKind.MATURITY, (organism.id,), organism.position)

    def _housekeeping(self, context: TickContext, organism: Organism) -> None:
        reproduction = organism.reproduction
        living_young = {young for young in reproduction.dependents if context.population.get(young) is not None}
        reproduction.dependents = living_young
        reproduction.lactating = reproduction.lactating and bool(living_young)
        reproduction.forget_old_courtship(context.tick, context.services.ecology.reproduction.courtship_memory_ticks)
        organism.social.decay_bonds(context.services.ecology.social.bond_half_life_ticks)
        record = context.records.get(organism.id)
        if record is None or not record.struck_by:
            organism.body.attacked_by = None
        organism.body.harassed_ticks = max(0, organism.body.harassed_ticks - 1)

    def _die(self, context: TickContext, organism: Organism, cause: DeathCause) -> None:
        tick = context.tick
        organism.die(tick, cause.value)
        world = context.world
        killer = organism.body.attacked_by if cause in (DeathCause.PREDATION, DeathCause.COMBAT) else None
        if cause not in NO_CARCASS_CAUSES:
            world.carcasses.create(
                organism.position,
                context.services.ecology.combat.carcass_meat_fraction * organism.body.mass_kg,
                organism.species_id,
                organism.id,
                organism.trait("toxicity"),
                organism.infection.strain_id,
            )
        world.sounds.emit(SoundEvent(organism.id, organism.species_id, organism.position, "scream", SCREAM_DB, False))
        context.population.retire(organism)
        world.dens.release_owner(organism.id)
        context.died.append(organism.id)
        context.emit(
            EventKind.DEATH,
            (organism.id,) + ((killer,) if killer else ()),
            organism.position,
            cause=cause.value,
            age=organism.body.age_ticks,
            species=organism.species_id,
        )
