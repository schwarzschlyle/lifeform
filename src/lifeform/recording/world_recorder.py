from __future__ import annotations

from collections import Counter
from pathlib import Path
from typing import Any

import numpy as np

from lifeform.config.run_config import RecordingSettings
from lifeform.core.events import DomainEvent, EventKind
from lifeform.ecology.mortality import DeathCause
from lifeform.evolution.speciation import Species
from lifeform.recording.chunks import ChunkWriter
from lifeform.recording.encoders import (
    CALL_NAMES,
    CONDITION_NAMES,
    TRACKED_TRAITS,
    VERB_NAMES,
    DecisionEncoder,
    FieldEncoder,
    FrameEncoder,
    organism_summary,
)
from lifeform.simulation.context import TickContext
from lifeform.simulation.engine import PHASE_ORDER, Simulation
from lifeform.world.terrain import TERRAIN, FoodLayer, TerrainType

TRAIT_SAMPLE_INTERVAL_TICKS = 12
ELEVATION_LEVELS = 255


class WorldRecorder:
    def __init__(self, directory: Path, simulation: Simulation, settings: RecordingSettings, brain_name: str) -> None:
        self._writer = ChunkWriter(directory)
        self._simulation = simulation
        self._settings = settings
        self._brain_name = brain_name
        self._frames_encoder = FrameEncoder(simulation.services)
        self._fields_encoder = FieldEncoder(simulation.world)
        self._decisions_encoder = DecisionEncoder(settings.decision_detail)
        self._frames: list[dict[str, Any]] = []
        self._fields: list[dict[str, Any]] = []
        self._decisions: list[dict[str, Any]] = []
        self._events: list[dict[str, Any]] = []
        self._stats: list[dict[str, Any]] = []
        self._organisms: dict[int, dict[str, Any]] = {}
        self._index: dict[str, list[list[Any]]] = {"frames": [], "fields": [], "decisions": []}
        self._chunk_start = 0
        self.calls = 0
        self.tokens = 0

    def start(self) -> None:
        world = self._simulation.world
        self._writer.write_packed("static.msgpack.gz", self._static())
        for organism in self._simulation.population.living():
            self._register(organism.id)
        self._frames.append(self._frames_encoder.frame(world, self._simulation.population.living(), None))
        self._fields.append(self._fields_encoder.keyframe(world))
        self._write_metadata("running")

    def on_tick(self, context: TickContext) -> None:
        world = context.world
        for organism_id in context.born:
            self._register(organism_id)
        for organism_id in context.died:
            self._register(organism_id)
        self._frames.append(self._frames_encoder.frame(world, context.population.living(), context))
        if context.tick % self._settings.field_keyframe_interval_ticks == 0:
            self._fields.append(self._fields_encoder.keyframe(world))
        self._events.extend(self._event(event) for event in context.events)
        self._record_decisions(context)
        self._stats.append(self._stats_row(context))
        if (context.tick + 1) % self._settings.chunk_ticks == 0:
            self._flush_chunk(context.tick)

    def finish(self, status: str) -> None:
        tick = self._simulation.tick
        if self._frames:
            self._flush_chunk(tick)
        for organism in self._simulation.population.living():
            self._organisms[organism.id] = self._summary(organism.id)
        species_names = self._simulation.services.species
        self._writer.write_packed("events.msgpack.gz", self._events)
        self._writer.write_packed("organisms.msgpack.gz", list(self._organisms.values()))
        self._writer.write_packed("stats.msgpack.gz", self._stats)
        self._writer.write_json(
            "species.json", [self._species_entry(species) for species in species_names.species.values()]
        )
        self._write_metadata(status)

    def _record_decisions(self, context: TickContext) -> None:
        tick_entries: list[dict[str, Any]] = []
        for organism_id, decision in context.decisions.items():
            self.calls += 1
            self.tokens += decision.input_tokens
            entry = self._decisions_encoder.record(context, organism_id)
            if entry is not None:
                tick_entries.append(entry)
        if self._settings.decision_detail != "none":
            self._decisions.append({"tick": context.tick, "decisions": tick_entries})

    def _flush_chunk(self, end_tick: int) -> None:
        start = self._chunk_start
        name = f"{start:06d}-{end_tick:06d}.msgpack.gz"
        self._writer.write_packed(f"frames/{name}", self._frames)
        self._index["frames"].append([start, end_tick, f"frames/{name}"])
        if self._fields:
            self._writer.write_packed(f"fields/{name}", self._fields)
            self._index["fields"].append([self._fields[0]["tick"], self._fields[-1]["tick"], f"fields/{name}"])
        if self._decisions:
            self._writer.write_packed(f"decisions/{name}", self._decisions)
            self._index["decisions"].append(
                [self._decisions[0]["tick"], self._decisions[-1]["tick"], f"decisions/{name}"]
            )
        self._frames, self._fields, self._decisions = [], [], []
        self._chunk_start = end_tick + 1
        self._writer.write_packed("events.msgpack.gz", self._events)
        self._writer.write_packed("stats.msgpack.gz", self._stats)
        self._write_metadata("running")

    def _static(self) -> dict[str, Any]:
        world = self._simulation.world
        elevation = world.elevation_m
        span = max(float(elevation.max()), 1.0)
        return {
            "width": world.width,
            "height": world.height,
            "terrain": world.terrain.astype(np.uint8).tobytes(),
            "elevation": (np.clip(elevation / span, 0.0, 1.0) * ELEVATION_LEVELS).astype(np.uint8).tobytes(),
            "elevation_max_m": span,
            "substellar": ((world.substellar_cosine + 1.0) / 2.0 * ELEVATION_LEVELS).astype(np.uint8).tobytes(),
        }

    def _write_metadata(self, status: str) -> None:
        world = self._simulation.world
        preset = world.preset
        self._writer.write_json(
            "index.json",
            {
                **self._index,
                "chunk_ticks": self._settings.chunk_ticks,
                "keyframe_interval": self._settings.field_keyframe_interval_ticks,
            },
        )
        self._writer.write_json(
            "world.json",
            {
                "slug": preset.slug,
                "title": preset.title,
                "biome": preset.biome,
                "description": preset.description,
                "question": preset.question,
                "palette": preset.palette,
                "tidally_locked": preset.climate.tidally_locked,
                "width": world.width,
                "height": world.height,
                "ticks_completed": self._simulation.tick,
                "status": status,
                "brain": self._brain_name,
                "calls": self.calls,
                "tokens": self.tokens,
                "productivity_scale": world.productivity_scale,
                "calendar": {
                    "ticks_per_day": world.calendar.ticks_per_day,
                    "ticks_per_season": world.calendar.ticks_per_season,
                    "season_names": list(world.calendar.season_names),
                },
                "field_scales": self._fields_encoder.scales,
                "terrain_types": [
                    {"id": int(terrain), "name": terrain.name.lower(), "description": TERRAIN.description(terrain)}
                    for terrain in TerrainType
                ],
                "food_layers": [layer.key for layer in FoodLayer],
                "verbs": VERB_NAMES,
                "call_names": CALL_NAMES,
                "conditions": CONDITION_NAMES,
                "death_causes": [cause.value for cause in DeathCause],
                "phase_order": list(PHASE_ORDER),
                "population": len(self._simulation.population),
            },
        )

    def _register(self, organism_id: int) -> None:
        self._organisms[organism_id] = self._summary(organism_id)

    def _summary(self, organism_id: int) -> dict[str, Any]:
        organism = self._simulation.population.any(organism_id)
        if organism is None:
            return self._organisms.get(organism_id, {"id": organism_id})
        return organism_summary(organism, self._simulation.services.species.name_of(organism.species_id))

    def _stats_row(self, context: TickContext) -> dict[str, Any]:
        population = context.population
        causes = Counter(str(event.payload.get("cause")) for event in context.events if event.kind == EventKind.DEATH)
        bands = Counter(intent.band.value for intent in context.intents.values())
        verbs = Counter(intent.affordance.verb.value for intent in context.intents.values())
        vegetation = context.world.fields.vegetation
        row: dict[str, Any] = {
            "tick": context.tick,
            "population": {str(key): value for key, value in population.species_counts().items()},
            "births": len(context.born),
            "deaths": dict(causes),
            "bands": dict(bands),
            "verbs": dict(verbs),
            "calls": len(context.decisions),
            "tokens": sum(decision.input_tokens for decision in context.decisions.values()),
            "vegetation": {layer.key: round(vegetation.total(layer), 2) for layer in FoodLayer},
            "carcasses": len(context.world.carcasses.items),
        }
        if context.tick % TRAIT_SAMPLE_INTERVAL_TICKS == 0:
            row["traits"] = self._trait_means(context)
        return row

    @staticmethod
    def _trait_means(context: TickContext) -> dict[str, dict[str, float]]:
        grouped: dict[int, list[Any]] = {}
        for organism in context.population.living():
            grouped.setdefault(organism.species_id, []).append(organism)
        means: dict[str, dict[str, float]] = {}
        for species_id, members in grouped.items():
            means[str(species_id)] = {
                name: round(float(np.mean([member.trait(name) for member in members])), 4) for name in TRACKED_TRAITS
            }
        return means

    @staticmethod
    def _event(event: DomainEvent) -> dict[str, Any]:
        return {
            "tick": event.tick,
            "kind": event.kind.value,
            "actors": list(event.actors),
            "position": list(event.position) if event.position else None,
            "payload": event.payload,
        }

    @staticmethod
    def _species_entry(species: Species) -> dict[str, Any]:
        return {
            "id": species.species_id,
            "name": species.name,
            "parent": species.parent_id,
            "origin_tick": species.origin_tick,
            "extinct_tick": species.extinct_tick,
            "hue": species.hue,
            "archetype": species.archetype,
            "peak_population": species.peak_population,
            "history": species.member_history,
        }
