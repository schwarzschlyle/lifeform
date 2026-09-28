from __future__ import annotations

from lifeform.core.events import EventKind
from lifeform.simulation.context import TickContext


class EvolutionPhase:
    name = "evolution"

    def run(self, context: TickContext) -> None:
        interval = context.services.ecology.evolution.clustering_interval_ticks
        if context.tick % interval != 0:
            return
        events = context.services.clusterer.cluster(context.population.living(), context.tick)
        for event in events:
            kind = EventKind.SPECIATION if event.kind == "speciation" else EventKind.EXTINCTION
            context.emit(kind, (event.species_id,), None, name=event.name, parent=event.parent_id)
        living_species = {species.species_id for species in context.services.species.living()}
        context.world.fields.scent.forget_musk_of(living_species)
