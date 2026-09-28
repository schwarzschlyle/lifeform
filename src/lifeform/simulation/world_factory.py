from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np

from lifeform.biology import allometry
from lifeform.biology.factory import Archetype
from lifeform.biology.genome import Genome
from lifeform.biology.organism import Organism
from lifeform.biology.phenotype import Development, Phenotype
from lifeform.config.loaders import ArchetypeLibrary, ecology_for
from lifeform.config.parameters import EcologyParameters
from lifeform.config.world_preset import FounderGroup, WorldPreset
from lifeform.core.geometry import Position
from lifeform.core.randomness import RandomStreams
from lifeform.simulation.budget import MIN_FOUNDERS_PER_GROUP
from lifeform.simulation.population import Population
from lifeform.simulation.services import Ecosystem
from lifeform.world.generation.blueprint import WorldBlueprint
from lifeform.world.generation.builder import WorldBuilder
from lifeform.world.terrain import IMPASSABLE, TERRAIN, FoodLayer, TerrainType
from lifeform.world.thermal_baseline import ThermalBaseline
from lifeform.world.world import World

FIELD_METABOLIC_MULTIPLE = 2.5
HARVEST_REACHABILITY = 0.4
ENVIRONMENT_FACTOR = 0.35
MIN_PRODUCTIVITY = 0.003
MAX_PRODUCTIVITY = 1.0
GROUP_SPREAD_PATCHES = 3
PLACEMENT_ATTEMPTS = 60
TEMPERATURE_TOLERANCE_C = 15.0
HERBIVORE_ANIMAL_DIET = 0.35
DEFAULT_ASSIMILATION = 0.5
CLIMATE_TOLERANT_SHARE = 0.3


@dataclass(slots=True)
class BuiltWorld:
    world: World
    population: Population
    services: Ecosystem


class ProductivityCalibrator:
    """Scales plant productivity so the land supports the preset's target number of plant-eaters."""

    def __init__(self, ecology: EcologyParameters) -> None:
        self._ecology = ecology

    def scale(
        self,
        preset: WorldPreset,
        blueprint: WorldBlueprint,
        founders: list[tuple[FounderGroup, Phenotype]],
        temperature: np.ndarray,
    ) -> float:
        demand = self._herbivore_demand_kg(preset, founders)
        supply = self._sustainable_yield_kg(blueprint, temperature)
        if supply <= 0.0 or demand <= 0.0:
            return MAX_PRODUCTIVITY
        return float(min(MAX_PRODUCTIVITY, max(MIN_PRODUCTIVITY, demand / supply)))

    def _herbivore_demand_kg(self, preset: WorldPreset, founders: list[tuple[FounderGroup, Phenotype]]) -> float:
        herbivores = [
            (group, phenotype) for group, phenotype in founders if phenotype.diet.animal < HERBIVORE_ANIMAL_DIET
        ]
        if not herbivores:
            return 0.0
        total_count = sum(group.count for group, _ in herbivores)
        need = 0.0
        for group, phenotype in herbivores:
            field_rate = (
                FIELD_METABOLIC_MULTIPLE
                * allometry.kleiber(phenotype.adult_mass_kg, self._ecology.metabolism.basal_eu_per_tick_per_kg075)
                * (phenotype.basal_multiplier)
            )
            energy_per_kg = self._plant_energy(phenotype)
            need += group.count / total_count * field_rate / energy_per_kg
        return need * preset.targets.herbivores

    def _plant_energy(self, phenotype: Phenotype) -> float:
        best = 0.0
        for layer in FoodLayer:
            parameters = self._ecology.food_layers[layer.key]
            weight = phenotype.diet.weight(parameters.diet_class)
            best = max(best, parameters.energy_density_eu_per_kg * parameters.max_assimilation * math.sqrt(weight))
        return best or DEFAULT_ASSIMILATION * self._ecology.food_layers["grass"].energy_density_eu_per_kg

    def _sustainable_yield_kg(self, blueprint: WorldBlueprint, temperature: np.ndarray) -> float:
        capacity = TERRAIN.capacity[blueprint.terrain]
        total = 0.0
        for layer in (
            FoodLayer.GRASS,
            FoodLayer.BROWSE,
            FoodLayer.FRUIT,
            FoodLayer.SEEDS,
            FoodLayer.ALGAE,
            FoodLayer.FUNGI,
        ):
            parameters = self._ecology.food_layers[layer.key]
            thermal = np.exp(-(((temperature - parameters.thermal_optimum_c) / parameters.thermal_breadth_c) ** 2))
            layer_yield = parameters.growth_rate_per_tick * capacity[..., layer] * thermal / 4.0
            total += float(layer_yield.sum())
        return total * ENVIRONMENT_FACTOR * HARVEST_REACHABILITY


class FounderPlacer:
    def __init__(self, world: World, rng: np.random.Generator) -> None:
        self._world = world
        self._rng = rng

    def suitability(self, phenotype: Phenotype) -> np.ndarray:
        world = self._world
        capacity = world.fields.vegetation.capacity
        food = np.zeros(capacity.shape[1:], dtype=np.float32)
        for layer in FoodLayer:
            weight = phenotype.diet.weight(world.ecology.food_layers[layer.key].diet_class)
            food += weight * capacity[layer] / max(float(capacity[layer].max()), 1e-6)
        if phenotype.diet.animal >= HERBIVORE_ANIMAL_DIET:
            food = food + phenotype.diet.animal
        temperature = world.climate.annual_mean_temperature()
        comfort = np.exp(-(((temperature - phenotype.trait("thermal_optimum")) / TEMPERATURE_TOLERANCE_C) ** 2))
        passable = ~np.isin(world.terrain, (TerrainType.DEEP_WATER, TerrainType.SHALLOW_WATER))
        comfort_weight = CLIMATE_TOLERANT_SHARE + (1.0 - CLIMATE_TOLERANT_SHARE) * comfort
        return (food * comfort_weight * passable).astype(np.float32)

    def centers(self, phenotype: Phenotype, count: int) -> list[Position]:
        weights = self.suitability(phenotype).ravel().astype(np.float64)
        if weights.sum() <= 0.0:
            weights = np.ones_like(weights)
        chosen = self._rng.choice(weights.size, size=count, p=weights / weights.sum())
        width = self._world.width
        return [Position(int(index % width), int(index // width)) for index in chosen]

    def near(self, center: Position, swim_skill: float) -> Position:
        world = self._world
        for _ in range(PLACEMENT_ATTEMPTS):
            dx, dy = (int(value) for value in self._rng.integers(-GROUP_SPREAD_PATCHES, GROUP_SPREAD_PATCHES + 1, 2))
            candidate = world.metric.wrap(center.x + dx, center.y + dy)
            dry_enough = world.terrain_at(candidate) != TerrainType.DEEP_WATER
            if dry_enough and world.move_cost(candidate, swim_skill) != IMPASSABLE:
                return candidate
        return center


class WorldFactory:
    def __init__(self, archetypes: ArchetypeLibrary) -> None:
        self._archetypes = archetypes

    def build(self, preset: WorldPreset, seed: int, population_scale: float) -> BuiltWorld:
        streams = RandomStreams(seed)
        ecology = ecology_for(preset)
        blueprint = WorldBuilder(preset, streams.stream("generation")).build()
        groups = self._scaled_groups(preset, population_scale)
        archetypes = {
            group.archetype: Archetype.from_mapping(self._archetypes.load(group.archetype), dict(group.overrides))
            for group in groups
        }
        probe = Development(ecology, streams.stream("calibration"))
        founders = [
            (group, probe.develop(Genome(np.stack([archetypes[group.archetype].base_genotype] * 2))))
            for group in groups
        ]
        scale = self._productivity(preset, ecology, blueprint, founders)
        world = World(preset, ecology, blueprint, scale, streams)
        services = Ecosystem.assemble(ecology, world, streams)
        population = Population(world.metric)
        self._found(world, services, population, groups, archetypes, streams)
        return BuiltWorld(world, population, services)

    @staticmethod
    def _scaled_groups(preset: WorldPreset, population_scale: float) -> list[FounderGroup]:
        scaled: list[FounderGroup] = []
        for group in preset.founders:
            count = max(MIN_FOUNDERS_PER_GROUP, round(group.count * population_scale))
            scaled.append(group.model_copy(update={"count": count, "groups": min(group.groups, count)}))
        return scaled

    @staticmethod
    def _productivity(
        preset: WorldPreset,
        ecology: EcologyParameters,
        blueprint: WorldBlueprint,
        founders: list[tuple[FounderGroup, Phenotype]],
    ) -> float:
        if preset.productivity_scale != "calibrated":
            return float(preset.productivity_scale)
        temperature = ThermalBaseline(preset.climate).annual_mean(blueprint.elevation_m, blueprint.substellar_cosine)
        return ProductivityCalibrator(ecology).scale(preset, blueprint, founders, temperature)

    def _found(
        self,
        world: World,
        services: Ecosystem,
        population: Population,
        groups: list[FounderGroup],
        archetypes: dict[str, Archetype],
        streams: RandomStreams,
    ) -> None:
        placer = FounderPlacer(world, streams.stream("placement"))
        for group in groups:
            archetype = archetypes[group.archetype]
            species = services.species.found(
                group.name or archetype.name, archetype.base_genotype, archetype.hue, 0, None, archetype.slug
            )
            probe = services.development.develop(Genome(np.stack([archetype.base_genotype] * 2)))
            centers = placer.centers(probe, group.groups)
            for index in range(group.count):
                center = centers[index % len(centers)]
                position = placer.near(center, probe.trait("swim_skill"))
                organism = services.factory.founder(
                    archetype, species.species_id, position, 0, world.temperature(position)
                )
                self._settle(organism, world)
                population.add(organism)
            species.peak_population = group.count

    @staticmethod
    def _settle(organism: Organism, world: World) -> None:
        water = world.drinkable_near(organism.position)
        if water is not None:
            organism.memory.spatial.remember("water", water, 1.0, 0)
