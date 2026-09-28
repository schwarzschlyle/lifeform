from __future__ import annotations

from lifeform.biology.physiology import Microclimate
from lifeform.core.events import EventKind
from lifeform.simulation.context import TickContext
from lifeform.simulation.disturbances import DisturbanceDirector

CONTACT_RADIUS = 1.5
MUSK_CRYPSIS_MASKING = 0.5
BLEEDING_SCENT_FRACTION = 0.2


class PhysiologyPhase:
    name = "physiology"

    def __init__(self, disturbances: DisturbanceDirector) -> None:
        self._disturbances = disturbances

    def run(self, context: TickContext) -> None:
        services = context.services
        world = context.world
        for organism in context.population.living():
            record = context.record(organism.id)
            position = organism.position
            climate = Microclimate(
                air_temperature_c=world.temperature(position),
                light=world.light(position),
                annual_mean_temperature_c=world.annual_mean_temperature(position),
                toxin_level=float(world.fields.toxin.level[position.y, position.x]),
                basking=record.basking,
                shaded=record.shaded,
                in_water=record.in_water,
                huddling=record.huddling,
                in_den=organism.body.in_den,
                brooded_at_c=self._brooding_temperature(context, organism.id),
                crowding=self._crowding(context, organism.id),
            )
            record.activity.extra_energy_eu += services.conception.pregnancy_cost(organism)
            disease_drain = services.transmission.progress(organism, world)
            report = services.physiology.advance(organism, record.activity, climate, context.tick, disease_drain)
            world.fields.nutrients.deposit(
                position.x, position.y, report.excreted_kg * services.ecology.digestion.excretion_nutrient_per_kg
            )
            if world.is_burning(position):
                organism.body.take_damage("fire", self._disturbances.fire_damage_per_tick, context.tick)
            self._emit_scents(context, organism.id)
        self._spread_disease(context)

    @staticmethod
    def _brooding_temperature(context: TickContext, organism_id: int) -> float | None:
        organism = context.population.organisms[organism_id]
        if organism.reproduction.weaned:
            return None
        mother = context.population.get(organism.reproduction.mother_id)
        if mother is None or not context.world.metric.are_adjacent(mother.position, organism.position):
            return None
        return mother.body.body_temperature_c

    @staticmethod
    def _crowding(context: TickContext, organism_id: int) -> int:
        organism = context.population.organisms[organism_id]
        return sum(
            1
            for other in context.population.within(organism.position, CONTACT_RADIUS)
            if other.species_id == organism.species_id and other.id != organism_id
        )

    @staticmethod
    def _emit_scents(context: TickContext, organism_id: int) -> None:
        organism = context.population.organisms[organism_id]
        scent = context.services.ecology.scent
        landscape = context.world.fields.scent
        position = organism.position
        masking = 1.0 - MUSK_CRYPSIS_MASKING * organism.trait("crypsis")
        channel = landscape.musk_channel(organism.species_id)
        landscape.emit(
            channel, position.x, position.y, scent.musk_emission_per_kg075 * organism.body.mass_kg**0.75 * masking
        )
        season = context.world.calendar.season_index(context.tick)
        if context.services.clock.in_estrus(organism, context.tick, season):
            landscape.emit(landscape.estrus_channel(organism.species_id), position.x, position.y, scent.estrus_emission)
        if organism.body.bleeding:
            landscape.emit("blood", position.x, position.y, scent.blood_emission_per_damage * BLEEDING_SCENT_FRACTION)

    @staticmethod
    def _spread_disease(context: TickContext) -> None:
        transmission = context.services.transmission
        for carrier in context.population.living():
            if not carrier.infection.infectious:
                continue
            for contact in context.population.within(carrier.position, CONTACT_RADIUS):
                if contact.id == carrier.id:
                    continue
                strain = transmission.contact(carrier, contact)
                if strain is not None:
                    context.emit(
                        EventKind.INFECTION, (contact.id, carrier.id), contact.position, strain=strain.strain_id
                    )
        for organism in context.population.living():
            record = context.records.get(organism.id)
            exposed_to_water = record is not None and (record.drank_litres > 0.0 or record.in_water)
            if exposed_to_water:
                strain = transmission.environmental_exposure(organism, context.world)
                if strain is not None:
                    context.emit(EventKind.INFECTION, (organism.id,), organism.position, strain=strain.strain_id)
