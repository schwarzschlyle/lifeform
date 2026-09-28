from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np

from lifeform.actions.calls import CALL_SPECS
from lifeform.actions.verbs import VERB_SPECS
from lifeform.biology import allometry
from lifeform.biology.factory import Archetype, OrganismFactory
from lifeform.biology.genome import GENES, GeneModule
from lifeform.biology.instincts import INSTINCT_BY_KEY, INSTINCTS
from lifeform.biology.mechanics import BodyMechanics
from lifeform.biology.organism import Organism
from lifeform.catalog.notes import (
    DEATH_NOTES,
    GENE_NOTES,
    GENE_UNITS,
    INSTINCT_NOTE,
    MARKER_NOTE,
    MODULE_NOTES,
    PHASE_NOTES,
    VERB_NOTES,
)
from lifeform.cognition.question_panel import (
    CALL_INSTRUCTIONS,
    EFFORT_INSTRUCTIONS,
    EFFORT_LEVELS,
    FOCUS_INSTRUCTIONS,
    PANEL_VERSION,
    THREAT_INSTRUCTIONS,
    THREAT_LEVELS,
    action_instructions,
)
from lifeform.cognition.vocabulary import TEMPERAMENT_WORDS, activity_word, temperament_word
from lifeform.config.brains import OFFLINE_SETTINGS, BrainLibrary, SystemOneSettings
from lifeform.config.loaders import ArchetypeLibrary, PresetLibrary
from lifeform.config.parameters import EcologyParameters
from lifeform.config.world_preset import CalendarConfig, WorldPreset
from lifeform.core.geometry import Position, TorusMetric
from lifeform.core.identifiers import IdSequence
from lifeform.core.time import Calendar
from lifeform.ecology.mortality import DeathCause
from lifeform.simulation.budget import DEFAULT_TOKENS_PER_CALL
from lifeform.simulation.engine import PHASE_ORDER
from lifeform.world.terrain import TERRAIN, FoodLayer, TerrainType

FIELD_METABOLIC_MULTIPLE = 2.5
DAYLIGHT = 1.0
MOONLIGHT = 0.05
ALL_OUT_EFFORT = 3
ENDOTHERM_THRESHOLD = 0.5
PROBE_TEMPERATURE_C = 20.0
PROBE_GRID = 32
DIGITS = 3


def _rounded(value: float) -> float:
    return round(float(value), DIGITS)


class ProjectCatalog:
    """Everything the landing page explains, derived from the code and configuration themselves."""

    def __init__(self, presets_directory: Path, archetypes_directory: Path, brains_path: Path) -> None:
        self._brains = BrainLibrary(brains_path)
        self._presets = PresetLibrary(presets_directory)
        self._archetypes = ArchetypeLibrary(archetypes_directory)
        self._archetypes_directory = archetypes_directory
        defaults = EcologyParameters()
        quiet_evolution = defaults.evolution.model_copy(
            update={"developmental_noise": 0.0, "founder_allele_noise": 0.0}
        )
        self._ecology = defaults.model_copy(update={"evolution": quiet_evolution})
        self._mechanics = BodyMechanics(self._ecology)
        calendar = CalendarConfig()
        self._calendar = Calendar(
            calendar.ticks_per_day, calendar.days_per_season, calendar.season_names, calendar.days_per_lunar_cycle
        )

    def build(self) -> dict[str, Any]:
        presets = self._presets.load_all()
        return {
            "jev": self._jev(),
            "brains": self.brains_facts(),
            "panel": self._panel(),
            "calendar": self._calendar_facts(),
            "phases": [{"name": name, "note": PHASE_NOTES[name]} for name in PHASE_ORDER],
            "modules": self._modules(),
            "genes": self._genes(),
            "instincts": [{"key": instinct.key, "wording": instinct.wording} for instinct in INSTINCTS],
            "verbs": self._verbs(),
            "calls": self._calls(),
            "terrain": self._terrain(),
            "food_layers": self._food_layers(),
            "death_causes": [{"name": cause.value, "note": DEATH_NOTES[cause]} for cause in DeathCause],
            "archetypes": self._species(presets),
            "worlds": [self._world(preset) for preset in presets],
        }

    def _jev(self) -> dict[str, Any]:
        settings = SystemOneSettings()
        return {
            "maker": "TypeSafe AI",
            "model": settings.model,
            "requests_per_minute": settings.requests_per_minute,
            "tokens_per_second": settings.tokens_per_second,
            "price_usd_per_million_input_tokens": settings.price_usd_per_million_input_tokens,
            "tokens_per_call": DEFAULT_TOKENS_PER_CALL,
            "questions_per_call": 5,
        }

    def brains_facts(self) -> dict[str, Any]:
        registry = self._brains.load()
        return {
            "active": registry.active,
            "providers": [
                {
                    "name": settings.name,
                    "title": settings.title,
                    "description": settings.description,
                    "model": settings.model,
                    "endpoint": settings.base_url or "offline",
                    "price_usd_per_million_input_tokens": settings.price_usd_per_million_input_tokens,
                    "host_usd_per_hour": settings.host_usd_per_hour,
                    "requests_per_minute": settings.requests_per_minute,
                }
                for settings in [*registry.providers.values(), OFFLINE_SETTINGS]
            ],
        }

    def _panel(self) -> dict[str, Any]:
        return {
            "version": PANEL_VERSION,
            "max_menu_options": self._ecology.cognition.max_menu_options,
            "interpretation": self._interpretation(),
            "questions": [
                {
                    "key": "action",
                    "type": "Choice",
                    "instructions": action_instructions(self._calendar.hours_per_tick),
                    "answers": ["one option from the menu of up to 32 legal actions"],
                },
                {"key": "effort", "type": "Score", "instructions": EFFORT_INSTRUCTIONS, "answers": list(EFFORT_LEVELS)},
                {"key": "threat", "type": "Score", "instructions": THREAT_INSTRUCTIONS, "answers": list(THREAT_LEVELS)},
                {
                    "key": "call",
                    "type": "Choice",
                    "instructions": CALL_INSTRUCTIONS,
                    "answers": [spec.description for spec in CALL_SPECS.values()],
                },
                {
                    "key": "focus",
                    "type": "Choice",
                    "instructions": FOCUS_INSTRUCTIONS,
                    "answers": ["one of the things it perceives, or nothing in particular"],
                },
            ],
        }

    def _interpretation(self) -> dict[str, Any]:
        cognition = self._ecology.cognition
        return {
            "min_decisiveness": cognition.min_decisiveness,
            "max_decisiveness": cognition.max_decisiveness,
            "hesitant_below": cognition.hesitation_high_base,
            "dithering_below": cognition.hesitation_low_base,
            "caution_span": cognition.hesitation_caution_span,
            "urgent_threat_level": THREAT_LEVELS[cognition.urgent_threat_level],
            "fear_integration_rate": cognition.fear_integration_rate,
            "max_state_tokens": cognition.max_state_tokens,
            "attention": {
                "entities": cognition.max_attention_entities,
                "smells": cognition.max_smells,
                "sounds": cognition.max_sounds,
                "memories": cognition.max_memories,
            },
        }

    def _calendar_facts(self) -> dict[str, Any]:
        calendar = self._calendar
        return {
            "ticks_per_day": calendar.ticks_per_day,
            "hours_per_tick": calendar.hours_per_tick,
            "days_per_season": calendar.days_per_season,
            "ticks_per_year": calendar.ticks_per_year,
        }

    @staticmethod
    def _modules() -> list[dict[str, Any]]:
        return [
            {"name": module.value, "note": MODULE_NOTES[module.value], "count": len(GENES.modules[module])}
            for module in GeneModule
        ]

    @staticmethod
    def _genes() -> list[dict[str, Any]]:
        genes: list[dict[str, Any]] = []
        for index, spec in enumerate(GENES.specs):
            if spec.module == GeneModule.INSTINCTS:
                key = spec.name.removeprefix("instinct:")
                note = f"{INSTINCT_NOTE} “{INSTINCT_BY_KEY[key].wording}”"
            elif spec.module == GeneModule.NEUTRAL:
                note = MARKER_NOTE
            else:
                note = GENE_NOTES[spec.name]
            genes.append(
                {
                    "index": index + 1,
                    "name": spec.name,
                    "module": spec.module.value,
                    "low": spec.low,
                    "high": spec.high,
                    "scale": spec.scale,
                    "unit": GENE_UNITS.get(spec.name, "0–1"),
                    "note": note,
                }
            )
        return genes

    @staticmethod
    def _verbs() -> list[dict[str, Any]]:
        return [
            {
                "name": verb.value,
                "family": spec.family.value,
                "pal": spec.pal,
                "moves": spec.moves,
                "note": VERB_NOTES[verb],
            }
            for verb, spec in VERB_SPECS.items()
        ]

    @staticmethod
    def _calls() -> list[dict[str, Any]]:
        return [
            {
                "name": call.value,
                "description": spec.description,
                "level_db": spec.level_db,
                "adults_only": spec.adults_only,
                "min_vocal_capacity": spec.min_vocal_capacity,
            }
            for call, spec in CALL_SPECS.items()
        ]

    @staticmethod
    def _terrain() -> list[dict[str, Any]]:
        rows: list[dict[str, Any]] = []
        for terrain in TerrainType:
            properties = TERRAIN[terrain]
            rows.append(
                {
                    "id": int(terrain),
                    "name": terrain.name.lower(),
                    "description": properties.description,
                    "move_cost": None if properties.move_cost == float("inf") else properties.move_cost,
                    "cover": properties.cover,
                    "sight_opacity": properties.sight_opacity,
                    "temperature_offset_c": properties.temperature_offset_c,
                    "food": {layer.key: amount for layer, amount in properties.capacity_kg.items()},
                }
            )
        return rows

    def _food_layers(self) -> list[dict[str, Any]]:
        return [{"key": layer.key, **self._ecology.food_layers[layer.key].model_dump()} for layer in FoodLayer]

    def _species(self, presets: list[WorldPreset]) -> list[dict[str, Any]]:
        slugs = sorted(path.stem for path in self._archetypes_directory.glob("*.yaml"))
        return [self._archetype(slug, presets) for slug in slugs]

    def _archetype(self, slug: str, presets: list[WorldPreset]) -> dict[str, Any]:
        data = self._archetypes.load(slug)
        archetype = Archetype.from_mapping(data, {})
        organism = self._probe(archetype)
        phenotype = organism.phenotype
        temperament = [
            word for trait in TEMPERAMENT_WORDS if (word := temperament_word(trait, phenotype.trait(trait))) is not None
        ]
        return {
            "slug": slug,
            "name": archetype.name,
            "summary": data.get("summary", ""),
            "hue": archetype.hue,
            "diet": {
                "fiber": _rounded(phenotype.diet.fiber),
                "soft": _rounded(phenotype.diet.soft),
                "animal": _rounded(phenotype.diet.animal),
            },
            "temperament": temperament,
            "rhythm": activity_word(phenotype.activity_phase),
            "instincts": [
                {"key": key, "wording": INSTINCT_BY_KEY[key].wording, "strength": _rounded(value)}
                for key, value in sorted(phenotype.instincts.items())
            ],
            "stats": self._stats(organism),
            "genes": self._gene_values(archetype),
            "worlds": self._appearances(slug, presets),
        }

    def _probe(self, archetype: Archetype) -> Organism:
        factory = OrganismFactory(
            self._ecology, TorusMetric(PROBE_GRID, PROBE_GRID), self._mechanics, np.random.default_rng(0), IdSequence()
        )
        return factory.founder(archetype, 1, Position(0, 0), 0, PROBE_TEMPERATURE_C)

    def _stats(self, organism: Organism) -> dict[str, Any]:
        mechanics = self._mechanics
        phenotype = organism.phenotype
        ticks_per_day = self._calendar.ticks_per_day
        basal = mechanics.basal_rate(organism)
        thermal = self._ecology.thermal
        conductance = allometry.thermal_conductance(organism.body.mass_kg, thermal.conductance_eu_per_c_per_kg05) * (
            1.0 - thermal.insulation_conductance_reduction * organism.trait("insulation")
        )
        endotherm = phenotype.endothermy >= ENDOTHERM_THRESHOLD
        return {
            "adult_mass_kg": _rounded(phenotype.adult_mass_kg),
            "lifespan_days": _rounded(phenotype.lifespan_ticks / ticks_per_day),
            "maturity_days": _rounded(phenotype.maturity_ticks / ticks_per_day),
            "gestation_days": _rounded(phenotype.gestation_ticks / ticks_per_day),
            "weaning_days": _rounded(phenotype.weaning_ticks / ticks_per_day),
            "litter_size": phenotype.litter_size,
            "top_speed_patches_per_tick": mechanics.top_speed(organism, 0),
            "basal_energy_per_tick": _rounded(basal),
            "fasting_days": _rounded(
                mechanics.energy_capacity(organism) / (FIELD_METABOLIC_MULTIPLE * basal) / ticks_per_day
            ),
            "stomach_kg": _rounded(mechanics.stomach_capacity(organism)),
            "bite_kg": _rounded(mechanics.bite_capacity(organism)),
            "vision_day_patches": _rounded(mechanics.vision_radius(organism, DAYLIGHT)),
            "vision_night_patches": _rounded(mechanics.vision_radius(organism, MOONLIGHT)),
            "hearing_threshold_db": _rounded(mechanics.hearing_threshold_db(organism)),
            "attack_power": _rounded(mechanics.attack_power(organism, ALL_OUT_EFFORT)),
            "defense": _rounded(mechanics.defense(organism)),
            "warm_blooded": endotherm,
            "comfortable_down_to_c": _rounded(thermal.endotherm_set_point_c - basal / max(conductance, 1e-6))
            if endotherm
            else None,
            "decisiveness_beta": _rounded(phenotype.decisiveness),
            "caution": _rounded(organism.trait("caution")),
            "thermal_optimum_c": _rounded(organism.trait("thermal_optimum")),
            "thermal_breadth_c": _rounded(organism.trait("thermal_breadth")),
        }

    @staticmethod
    def _gene_values(archetype: Archetype) -> list[dict[str, Any]]:
        values: list[dict[str, Any]] = []
        for index, spec in enumerate(GENES.specs):
            if spec.module in (GeneModule.INSTINCTS, GeneModule.NEUTRAL):
                continue
            fraction = float(archetype.base_genotype[index])
            values.append(
                {
                    "name": spec.name,
                    "module": spec.module.value,
                    "fraction": _rounded(fraction),
                    "value": _rounded(spec.express(fraction)),
                    "unit": GENE_UNITS.get(spec.name, "0–1"),
                }
            )
        return values

    @staticmethod
    def _appearances(slug: str, presets: list[WorldPreset]) -> list[dict[str, Any]]:
        return [
            {
                "world": preset.title,
                "slug": preset.slug,
                "count": group.count,
                "local_name": group.name,
                "overrides": dict(group.overrides),
            }
            for preset in presets
            for group in preset.founders
            if group.archetype == slug
        ]

    @staticmethod
    def _world(preset: WorldPreset) -> dict[str, Any]:
        climate = preset.climate
        return {
            "slug": preset.slug,
            "title": preset.title,
            "biome": preset.biome,
            "description": preset.description,
            "question": preset.question,
            "palette": preset.palette,
            "stretch": preset.stretch,
            "grid": [preset.grid.width, preset.grid.height],
            "default_ticks": preset.default_ticks,
            "seasons": list(preset.calendar.season_names),
            "climate": {
                "equator_temperature_c": climate.equator_temperature_c,
                "seasonal_amplitude_c": climate.seasonal_amplitude_c,
                "diurnal_amplitude_c": climate.diurnal_amplitude_c,
                "weather": climate.weather_profile.replace("_", " "),
                "tidally_locked": climate.tidally_locked,
                "moving_rain_belt": climate.rain_belt is not None,
            },
            "water_fraction": preset.terrain.water_fraction,
            "features": sorted({stamp.kind for stamp in preset.terrain.feature_stamps}),
            "disturbances": ProjectCatalog._disturbances(preset),
            "founders": [
                {
                    "archetype": group.archetype,
                    "name": group.name,
                    "count": group.count,
                    "groups": group.groups,
                    "overrides": dict(group.overrides),
                }
                for group in preset.founders
            ],
            "targets": preset.targets.model_dump(),
        }

    @staticmethod
    def _disturbances(preset: WorldPreset) -> list[str]:
        config = preset.disturbances
        notes: list[str] = []
        if config.lightning_fire_probability > 0.0:
            notes.append("wildfires lit by lightning in storms")
        if config.flood_pulse is not None:
            notes.append("a yearly flood pulse")
        notes.extend(f"drought from tick {drought.tick}" for drought in config.droughts)
        notes.extend(f"major eruption at tick {eruption.tick}" for eruption in config.eruptions)
        if config.eruption_rate_per_tick > 0.0:
            notes.append("occasional minor eruptions")
        if config.rift is not None:
            notes.append(f"a rift splits the land from tick {config.rift.open_tick}")
        if config.epidemic is not None:
            notes.append(f"a new disease appears at tick {config.epidemic.tick}")
        if config.rafting_probability > 0.0:
            notes.append("rare rafting between islands")
        if preset.climate.drift is not None:
            notes.append(f"climate drifts {preset.climate.drift.total_c:+.0f} °C over the run")
        if preset.climate.regional_drifts:
            notes.append("the two halves drift to different climates")
        return notes
