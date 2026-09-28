from __future__ import annotations

from dataclasses import dataclass

from lifeform.actions.verbs import Verb
from lifeform.biology import allometry
from lifeform.biology.body import MEAT_KEY, CarriedFood
from lifeform.biology.organism import Organism
from lifeform.core.events import EventKind
from lifeform.ecology.predation import StrikeCircumstances
from lifeform.simulation.context import TickContext
from lifeform.simulation.resolution.movement import MovementReport
from lifeform.simulation.resolution.signals import SignalEmitter
from lifeform.world.terrain import TerrainType

ADJACENT = 1.5
DISPLAY_RANGE = 3.0
COURT_RANGE = 2.5
GROUP_RADIUS = 2.0
CLIMB_REACH = 0.5
DEN_REACH = 0.6
FIGHT_NOISE_DB = 70.0
GROOM_PARASITE_RELIEF = 0.2
SELF_GROOM_RELIEF = 0.08
WALLOW_RELIEF = 0.15
GROOM_STRESS_RELIEF = 0.1
BOND_GAIN = 0.1
CARRY_MASS_FRACTION = 0.15
DEN_WORK_TICKS = 3
SUCKLE_ALONE_FRACTION = 0.5
MILK_WATER_LITRES_PER_KEU = 0.05
STRIKING_VERBS = frozenset({Verb.ATTACK, Verb.CHASE, Verb.FIGHT_BACK})
RETALIATING_VERBS = frozenset({Verb.BRACE, Verb.DEFEND_YOUNG, Verb.FIGHT_BACK, Verb.ATTACK})
STEALTHY_VERBS = frozenset({Verb.STALK.value, Verb.AMBUSH.value})
AMBUSH_EFFORT = 3
RIVAL_VALENCE = -0.3
MATE_VALENCE = 0.5
GROOMER_VALENCE = 0.4
SHARER_VALENCE = 0.5
EU_PER_KILO_EU = 1000.0
NO_ORIGIN = -1


@dataclass(slots=True)
class Engagement:
    attacker: Organism
    defender: Organism
    effort: int
    ambush: bool = False


class InteractionResolver:
    def __init__(self, signals: SignalEmitter) -> None:
        self._signals = signals

    def resolve(self, context: TickContext, report: MovementReport) -> None:
        self._strikes(context, report)
        self._mobs(context)
        self._contests(context)
        self._displays(context)
        self._courtship(context)
        self._mating(context)
        self._grooming(context)
        self._nursing(context)
        self._food_handling(context)
        self._dens(context)

    def _intent_verb(self, context: TickContext, organism: Organism) -> Verb | None:
        intent = context.intents.get(organism.id)
        return None if intent is None or intent.stalled else intent.affordance.verb

    def _target(self, context: TickContext, organism: Organism) -> Organism | None:
        intent = context.intents.get(organism.id)
        if intent is None or intent.affordance.target_id is None:
            return None
        target = context.population.get(intent.affordance.target_id)
        return target if target is not None and target.alive else None

    def _adjacent(self, context: TickContext, first: Organism, second: Organism, reach: float = ADJACENT) -> bool:
        return context.world.metric.distance(first.position, second.position) <= reach

    def _strikes(self, context: TickContext, report: MovementReport) -> None:
        engagements: list[Engagement] = []
        for organism in context.population.living():
            verb = self._intent_verb(context, organism)
            target = self._target(context, organism)
            if verb in STRIKING_VERBS and target is not None and self._adjacent(context, organism, target):
                engagements.append(Engagement(organism, target, context.intents[organism.id].effort))
        for ambusher_id, prey_id in report.ambush_triggers:
            ambusher = context.population.get(ambusher_id)
            prey = context.population.get(prey_id)
            if ambusher is not None and prey is not None:
                engagements.append(Engagement(ambusher, prey, AMBUSH_EFFORT, ambush=True))
        pressure: dict[int, int] = {}
        for engagement in engagements:
            pressure[engagement.defender.id] = pressure.get(engagement.defender.id, 0) + 1
        for engagement in engagements:
            self._engage(context, engagement, pressure[engagement.defender.id] - 1)

    def _engage(self, context: TickContext, engagement: Engagement, co_attackers: int) -> None:
        attacker, defender = engagement.attacker, engagement.defender
        if (
            attacker.body.health <= 0.0
            or defender.body.health <= 0.0
            or not self._reachable(attacker, defender, context)
        ):
            return
        guardian = self._guardian(context, attacker, defender)
        if guardian is not None:
            self._strike(context, guardian, attacker, context.intents[guardian.id].effort, 0, counter=True)
            if attacker.body.health <= 0.0:
                return
        self._strike(
            context,
            attacker,
            defender,
            engagement.effort,
            co_attackers,
            counter=False,
            stalked=engagement.ambush or self._stalked(context, attacker, defender),
        )
        verb = self._intent_verb(context, defender)
        target = self._target(context, defender)
        retaliates = verb in RETALIATING_VERBS and (verb in (Verb.BRACE, Verb.DEFEND_YOUNG) or target is attacker)
        if retaliates and defender.body.health > 0.0 and attacker.body.health > 0.0:
            self._strike(context, defender, attacker, context.intents[defender.id].effort, 0, counter=True)

    def _strike(
        self,
        context: TickContext,
        attacker: Organism,
        defender: Organism,
        effort: int,
        co_attackers: int,
        counter: bool,
        stalked: bool = False,
    ) -> None:
        circumstances = StrikeCircumstances(
            effort=effort,
            surprise=not counter and (defender.body.asleep or not context.perceived(defender.id, attacker.id)),
            stalked=stalked,
            co_attackers=co_attackers,
            defender_group=self._group_size(context, defender),
            cover=context.world.cover(defender.position),
            braced=defender.body.braced,
        )
        result = context.services.attacks.strike(attacker, defender, circumstances, context.tick)
        defender.body.asleep = False
        context.record(attacker.id).struck.append(defender.id)
        context.record(defender.id).struck_by.append(attacker.id)
        self._signals.emit_noise(context, attacker.id, "fight", FIGHT_NOISE_DB)
        if result.hit:
            scent = context.services.ecology.scent
            position = defender.position
            context.world.fields.scent.emit(
                "blood", position.x, position.y, scent.blood_emission_per_damage * result.damage
            )
            context.world.fields.scent.emit("alarm_pheromone", position.x, position.y, scent.alarm_emission)
        context.emit(
            EventKind.STRIKE,
            (attacker.id, defender.id),
            defender.position,
            hit=result.hit,
            damage=round(result.damage, 4),
            probability=round(result.probability, 3),
            killed=result.killed,
        )

    def _reachable(self, attacker: Organism, defender: Organism, context: TickContext) -> bool:
        if defender.body.climbing and attacker.trait("climb_skill") < CLIMB_REACH:
            return False
        if defender.body.in_den and attacker.trait("dig_skill") < DEN_REACH:
            return False
        deep = context.world.terrain_at(defender.position) == TerrainType.DEEP_WATER
        return not deep or context.services.mechanics.can_swim_deep(attacker)

    def _stalked(self, context: TickContext, attacker: Organism, defender: Organism) -> bool:
        previous = list(attacker.body.last_actions)[-2:-1]
        return bool(previous) and previous[0] in STEALTHY_VERBS and not context.perceived(defender.id, attacker.id)

    def _guardian(self, context: TickContext, attacker: Organism, defender: Organism) -> Organism | None:
        mother = context.population.get(defender.reproduction.mother_id)
        if mother is None or defender.reproduction.weaned:
            return None
        guarding = self._intent_verb(context, mother) == Verb.DEFEND_YOUNG
        return mother if guarding and self._adjacent(context, mother, attacker) else None

    def _group_size(self, context: TickContext, organism: Organism) -> int:
        return sum(
            1
            for other in context.population.within(organism.position, GROUP_RADIUS)
            if other.species_id == organism.species_id and other.id != organism.id
        )

    def _mobs(self, context: TickContext) -> None:
        for organism in context.population.living():
            target = self._target(context, organism)
            if (
                self._intent_verb(context, organism) == Verb.MOB
                and target is not None
                and self._adjacent(context, organism, target)
            ):
                context.services.attacks.mob(organism, target, context.tick)
                context.record(target.id).struck_by.append(organism.id)

    def _contests(self, context: TickContext) -> None:
        contests = context.services.contests
        for organism in context.population.living():
            target = self._target(context, organism)
            if self._intent_verb(context, organism) != Verb.CHALLENGE or target is None:
                continue
            if not self._adjacent(context, organism, target) or organism.body.health <= 0.0:
                continue
            reply = self._intent_verb(context, target)
            if reply in (Verb.SUBMIT, Verb.FLEE):
                winner, loser = organism, target
            else:
                winner, loser = contests.display_contest(organism, target)
            contests.settle(winner, loser, context.tick)
            loser.memory.social.note(winner.id, winner.species_id, "rival", RIVAL_VALENCE, context.tick)
            loser.memory.episodic.record(context.tick, f"you lost a dominance contest to {winner.identity.name}")
            context.emit(EventKind.CONTEST, (winner.id, loser.id), winner.position)

    def _displays(self, context: TickContext) -> None:
        for organism in context.population.living():
            target = self._target(context, organism)
            if self._intent_verb(context, organism) != Verb.THREAT_DISPLAY or target is None:
                continue
            if self._adjacent(context, organism, target, DISPLAY_RANGE):
                context.persistent.threatened_by[target.id] = organism.id
                context.record(target.id).threatened_by = organism.id

    def _courtship(self, context: TickContext) -> None:
        clock = context.services.clock
        season = context.world.calendar.season_index(context.tick)
        for organism in context.population.living():
            target = self._target(context, organism)
            if self._intent_verb(context, organism) != Verb.COURT or target is None:
                continue
            eligible = clock.eligible(organism, season) and clock.eligible(target, season)
            if eligible and self._adjacent(context, organism, target, COURT_RANGE):
                target.reproduction.courted_by[organism.id] = context.tick
                organism.reproduction.courting[target.id] = context.tick

    def _mating(self, context: TickContext) -> None:
        memory = context.services.ecology.reproduction.courtship_memory_ticks
        clock = context.services.clock
        season = context.world.calendar.season_index(context.tick)
        for organism in context.population.living():
            partner = self._target(context, organism)
            if self._intent_verb(context, organism) != Verb.MATE_WITH or partner is None:
                continue
            courted = context.tick - organism.reproduction.courted_by.get(partner.id, -10_000) <= memory
            if not (courted and self._adjacent(context, organism, partner)):
                continue
            if not (clock.eligible(organism, season) and clock.eligible(partner, season)):
                continue
            self._consummate(context, organism, partner)

    def _consummate(self, context: TickContext, chooser: Organism, suitor: Organism) -> None:
        female, male = (chooser, suitor) if chooser.reproduction.is_female else (suitor, chooser)
        context.record(female.id).mated_with = male.id
        context.record(male.id).mated_with = female.id
        chooser.reproduction.courted_by.pop(suitor.id, None)
        for partner, other in ((female, male), (male, female)):
            partner.memory.social.note(other.id, other.species_id, "mate", MATE_VALENCE, context.tick)
        context.emit(EventKind.MATING, (female.id, male.id), female.position)
        pregnancy = context.services.conception.attempt(female, male, context.tick)
        if pregnancy is not None:
            female.reproduction.pregnancy = pregnancy
            context.emit(
                EventKind.CONCEPTION,
                (female.id, male.id),
                female.position,
                due_tick=pregnancy.due_tick,
                litter_size=pregnancy.litter_size,
            )

    def _grooming(self, context: TickContext) -> None:
        for organism in context.population.living():
            verb = self._intent_verb(context, organism)
            body = organism.body
            if verb == Verb.GROOM_SELF:
                body.parasite_load = max(0.0, body.parasite_load - SELF_GROOM_RELIEF)
            elif verb == Verb.WALLOW:
                body.parasite_load = max(0.0, body.parasite_load - WALLOW_RELIEF)
            elif verb == Verb.GROOM:
                target = self._target(context, organism)
                if target is None or not self._adjacent(context, organism, target):
                    continue
                target.body.parasite_load = max(0.0, target.body.parasite_load - GROOM_PARASITE_RELIEF)
                target.body.stress = max(0.0, target.body.stress - GROOM_STRESS_RELIEF)
                organism.social.strengthen_bond(target.id, BOND_GAIN)
                target.social.strengthen_bond(organism.id, BOND_GAIN)
                target.memory.social.note(organism.id, organism.species_id, "ally", GROOMER_VALENCE, context.tick)
                context.record(target.id).groomed_by.append(organism.id)

    def _nursing(self, context: TickContext) -> None:
        for organism in context.population.living():
            verb = self._intent_verb(context, organism)
            if verb == Verb.NURSE and organism.reproduction.lactating:
                litter = [
                    young
                    for young_id in organism.reproduction.dependents
                    if (young := context.population.get(young_id)) is not None
                    and self._adjacent(context, organism, young)
                ]
                for young in litter:
                    self._transfer_milk(context, organism, young, 1.0 / len(litter))
            elif verb == Verb.SUCKLE:
                mother = context.population.get(organism.reproduction.mother_id)
                if mother is None or not mother.reproduction.lactating or not self._adjacent(context, mother, organism):
                    continue
                mother_nursing = self._intent_verb(context, mother) == Verb.NURSE
                if not mother_nursing:
                    self._transfer_milk(context, mother, organism, SUCKLE_ALONE_FRACTION)

    def _transfer_milk(self, context: TickContext, mother: Organism, young: Organism, fraction: float) -> None:
        reproduction = context.services.ecology.reproduction
        mechanics = context.services.mechanics
        deficit = max(0.0, mechanics.energy_capacity(young) - young.body.energy_eu)
        supply = fraction * allometry.kleiber(mother.body.mass_kg, reproduction.nursing_eu_per_tick_per_kg075)
        delivered = min(deficit / reproduction.nursing_efficiency, supply, mother.body.energy_eu)
        if delivered <= 0.0:
            return
        young.body.energy_eu += delivered * reproduction.nursing_efficiency
        young.body.hydration = min(
            1.0,
            young.body.hydration
            + MILK_WATER_LITRES_PER_KEU * delivered / EU_PER_KILO_EU / max(mechanics.body_water_litres(young), 1e-6),
        )
        context.record(mother.id).activity.extra_energy_eu += delivered * reproduction.mother_nursing_cost_multiplier
        context.record(young.id).ate_kg += delivered / EU_PER_KILO_EU

    def _food_handling(self, context: TickContext) -> None:
        world = context.world
        for organism in context.population.living():
            verb = self._intent_verb(context, organism)
            if verb == Verb.CARRY_FOOD:
                self._carry(context, organism)
            elif verb == Verb.SHARE_FOOD:
                target = self._target(context, organism)
                if (
                    target is not None
                    and organism.body.carrying is not None
                    and self._adjacent(context, organism, target)
                ):
                    self._give(organism, target)
                    target.memory.social.note(organism.id, organism.species_id, "ally", SHARER_VALENCE, context.tick)
            elif verb == Verb.STEAL_FOOD:
                target = self._target(context, organism)
                if (
                    target is not None
                    and target.body.carrying is not None
                    and self._adjacent(context, organism, target)
                ):
                    winner, _ = context.services.contests.display_contest(organism, target)
                    if winner is organism and organism.body.carrying is None:
                        organism.body.carrying, target.body.carrying = target.body.carrying, None
            elif verb in (Verb.CACHE_FOOD, Verb.DROP_FOOD) and organism.body.carrying is not None:
                self._store(context, organism, remember=verb == Verb.CACHE_FOOD)
        world.caches.prune()

    def _carry(self, context: TickContext, organism: Organism) -> None:
        intent = context.intents[organism.id]
        carcass = context.world.carcasses.items.get(intent.affordance.target_id or -1)
        if carcass is None or organism.body.carrying is not None:
            return
        if not context.world.metric.are_adjacent(organism.position, carcass.position):
            return
        chunk = min(CARRY_MASS_FRACTION * organism.body.mass_kg, carcass.mass_kg)
        carcass.mass_kg -= chunk
        organism.body.carrying = CarriedFood(MEAT_KEY, chunk, carcass.species_id)

    @staticmethod
    def _give(giver: Organism, receiver: Organism) -> None:
        carried = giver.body.carrying
        if carried is None:
            return
        receiver.body.add_to_stomach(carried.food_key, carried.mass_kg)
        giver.body.carrying = None

    @staticmethod
    def _store(context: TickContext, organism: Organism, remember: bool) -> None:
        carried = organism.body.carrying
        if carried is None:
            return
        position = organism.position
        if carried.food_key == MEAT_KEY:
            context.world.carcasses.create(position, carried.mass_kg, carried.origin_species_id, NO_ORIGIN, 0.0, None)
        else:
            context.world.caches.store(organism.id, position, carried.food_key, carried.mass_kg)
        if remember:
            organism.memory.spatial.remember(
                MEAT_KEY if carried.food_key == MEAT_KEY else f"food:{carried.food_key}",
                position,
                carried.mass_kg,
                context.tick,
            )
        organism.body.carrying = None

    def _dens(self, context: TickContext) -> None:
        for organism in context.population.living():
            if self._intent_verb(context, organism) != Verb.DIG_DEN:
                continue
            den = context.world.dens.advance_project(organism.id, organism.position, DEN_WORK_TICKS)
            if den is not None:
                organism.memory.spatial.remember("den", organism.position, 1.0, context.tick)
                context.emit(EventKind.DEN_BUILT, (organism.id,), organism.position)
