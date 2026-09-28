from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, field_validator


class FrozenModel(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class MetabolismParameters(FrozenModel):
    basal_eu_per_tick_per_kg075: float = 24.0
    ectotherm_basal_fraction: float = 0.15
    fat_energy_density_eu_per_kg: float = 39_000.0
    lean_energy_density_eu_per_kg: float = 7_000.0
    locomotion_eu_per_patch_per_kg068: float = 10.0
    starvation_damage_per_basal_deficit: float = 0.02
    lethal_lean_mass_fraction: float = 0.6
    weaponry_cost: float = 0.10
    toxicity_cost: float = 0.15
    immune_cost: float = 0.12
    sense_cost_each: float = 0.04
    stamina_cost: float = 0.05
    toxin_resistance_cost: float = 0.06
    attention_cost: float = 0.03
    healing_cost_eu_per_health_per_kg075: float = 200.0


class ThermalParameters(FrozenModel):
    endotherm_set_point_c: float = 37.5
    conductance_eu_per_c_per_kg05: float = 5.0
    insulation_conductance_reduction: float = 0.7
    thermoneutral_width_c: float = 12.0
    evaporative_water_fraction_per_c: float = 0.0015
    ectotherm_relaxation_per_tick_per_kg033: float = 0.6
    basking_gain_c: float = 10.0
    shade_cooling_c: float = 6.0
    water_cooling_c: float = 4.0
    q10: float = 2.5
    reference_temperature_c: float = 25.0
    thermal_damage_per_c_beyond_limit: float = 0.01
    den_air_weight: float = 0.3


class WaterParameters(FrozenModel):
    turnover_litres_per_tick_per_kg08: float = 0.01
    body_water_fraction: float = 0.6
    efficiency_reduction: float = 0.6
    drink_litres_per_tick_per_kg08: float = 0.4
    impaired_hydration: float = 0.3
    damaging_hydration: float = 0.1
    dehydration_damage_per_tick: float = 0.05
    lethal_dry_ticks: int = 2


class DigestionParameters(FrozenModel):
    stomach_capacity_fraction_of_mass: float = 0.06
    bite_kg_per_tick_per_kg075: float = 0.03
    excretion_nutrient_per_kg: float = 0.002


class SleepParameters(FrozenModel):
    wake_time_constant_ticks: float = 14.0
    sleep_time_constant_ticks: float = 3.0
    circadian_weight: float = 0.3
    deprivation_threshold: float = 0.85
    deprivation_perception_factor: float = 0.7


class StaminaParameters(FrozenModel):
    hurried_cost_per_tick: float = 0.15
    recovery_per_tick: float = 0.2
    rest_recovery_per_tick: float = 0.35


class HealthParameters(FrozenModel):
    healing_per_tick_per_kg_minus025: float = 0.02
    rest_healing_multiplier: float = 2.0
    bleeding_damage_per_tick: float = 0.02
    bleeding_stop_probability: float = 0.3
    limp_wound_threshold: float = 0.3
    limp_speed_factor: float = 0.6
    pain_half_life_ticks: float = 3.0
    toxin_clearance_per_tick: float = 0.03
    toxin_damage_per_tick_per_load: float = 0.04


class AgingParameters(FrozenModel):
    background_hazard_per_tick: float = 1e-5
    gompertz_scale: float = 2e-5
    gompertz_rate: float = 6.0
    senescence_onset_fraction: float = 0.6


class LifeHistoryParameters(FrozenModel):
    lifespan_ticks_per_kg025: float = 757.0
    maturity_ticks_per_kg025: float = 100.0
    gestation_ticks_per_kg025: float = 28.6
    weaning_ticks_per_kg025: float = 32.0
    litter_mass_fraction: float = 0.08
    max_litter_size: int = 8
    litter_size_exponent: float = 1.5
    precocial_litter_mass_gain: float = 0.5
    longevity_base: float = 0.6
    longevity_span: float = 0.8
    maturity_base: float = 1.4
    maturity_rate_span: float = 0.8
    gestation_base: float = 0.7
    gestation_precocial_span: float = 0.6
    weaning_base: float = 1.2
    weaning_precocial_span: float = 0.5
    growth_coefficient_per_tick: float = 0.1
    construction_energy_discount: float = 0.08
    juvenile_growth_energy_floor: float = 0.2
    adult_growth_energy_floor: float = 0.4
    adult_mass_fraction_for_maturity: float = 0.7


class LocomotionParameters(FrozenModel):
    speed_coefficient: float = 1.9
    speed_mass_exponent: float = 0.17
    max_patches_per_tick: int = 5
    climb_mass_limit_kg: float = 60.0


class CombatParameters(FrozenModel):
    attack_coefficient: float = 1.0
    defense_coefficient: float = 1.0
    wound_capacity_coefficient: float = 3.0
    agility_defense_weight: float = 0.5
    bias: float = -1.0
    power_ratio_weight: float = 1.2
    surprise_weight: float = 1.5
    stalk_weight: float = 0.8
    pack_weight: float = 0.6
    confusion_weight: float = 0.5
    cover_weight: float = 0.8
    fatigue_weight: float = 1.0
    brace_weight: float = 0.9
    armor_damage_reduction: float = 0.7
    passive_retaliation_fraction: float = 0.3
    carcass_meat_fraction: float = 0.6
    mob_damage_fraction: float = 0.15


class ReproductionParameters(FrozenModel):
    female_energy_threshold: float = 0.4
    male_energy_threshold: float = 0.3
    female_health_threshold: float = 0.5
    male_health_threshold: float = 0.4
    estrus_cycle_ticks: int = 48
    estrus_duration_ticks: int = 12
    courtship_memory_ticks: int = 2
    isolation_distance: float = 0.22
    pregnancy_cost_multiplier: float = 1.5
    miscarriage_energy_fraction: float = 0.15
    miscarriage_probability_per_tick: float = 0.05
    birth_complication_base: float = 0.005
    nursing_eu_per_tick_per_kg075: float = 100.0
    nursing_efficiency: float = 0.8
    mother_nursing_cost_multiplier: float = 1.25
    newborn_reserve_fraction: float = 0.5
    brooding_weight: float = 0.6


class DiseaseParameters(FrozenModel):
    susceptibility_immune_reduction: float = 0.8
    stress_susceptibility: float = 0.5
    environment_transmission: float = 0.05
    strain_mutation_probability: float = 0.05
    virulence_mutation_sigma: float = 0.1
    transmission_ceiling: float = 0.25
    water_diffusion: float = 0.15
    field_extinction_level: float = 1e-5
    virulence_half_saturation: float = 0.02
    parasite_gain_per_neighbor: float = 0.01
    parasite_drain_fraction_of_basal: float = 0.1


class SocialParameters(FrozenModel):
    elo_k_factor: float = 32.0
    initial_rating: float = 1000.0
    defeat_memory_ticks: int = 24
    group_radius_patches: int = 3
    bond_half_life_ticks: float = 48.0
    territory_mark_half_life_ticks: float = 36.0


class FoodLayerParameters(FrozenModel):
    energy_density_eu_per_kg: float
    growth_rate_per_tick: float
    thermal_optimum_c: float
    thermal_breadth_c: float
    needs_light: bool
    diet_class: str
    handling_factor: float
    digestion_rate_per_tick: float
    max_assimilation: float
    water_fraction: float
    dispersal_rate: float
    seed_floor_kg: float


def default_food_layers() -> dict[str, FoodLayerParameters]:
    return {
        "grass": FoodLayerParameters(
            energy_density_eu_per_kg=17_000,
            growth_rate_per_tick=0.012,
            thermal_optimum_c=24,
            thermal_breadth_c=14,
            needs_light=True,
            diet_class="fiber",
            handling_factor=1.0,
            digestion_rate_per_tick=0.25,
            max_assimilation=0.55,
            water_fraction=0.45,
            dispersal_rate=0.02,
            seed_floor_kg=0.0005,
        ),
        "browse": FoodLayerParameters(
            energy_density_eu_per_kg=16_000,
            growth_rate_per_tick=0.008,
            thermal_optimum_c=20,
            thermal_breadth_c=16,
            needs_light=True,
            diet_class="fiber",
            handling_factor=0.7,
            digestion_rate_per_tick=0.25,
            max_assimilation=0.50,
            water_fraction=0.5,
            dispersal_rate=0.01,
            seed_floor_kg=0.0005,
        ),
        "fruit": FoodLayerParameters(
            energy_density_eu_per_kg=20_000,
            growth_rate_per_tick=0.015,
            thermal_optimum_c=26,
            thermal_breadth_c=10,
            needs_light=True,
            diet_class="soft",
            handling_factor=1.2,
            digestion_rate_per_tick=0.45,
            max_assimilation=0.80,
            water_fraction=0.8,
            dispersal_rate=0.005,
            seed_floor_kg=0.0002,
        ),
        "seeds": FoodLayerParameters(
            energy_density_eu_per_kg=22_000,
            growth_rate_per_tick=0.006,
            thermal_optimum_c=22,
            thermal_breadth_c=16,
            needs_light=True,
            diet_class="soft",
            handling_factor=0.4,
            digestion_rate_per_tick=0.35,
            max_assimilation=0.75,
            water_fraction=0.1,
            dispersal_rate=0.01,
            seed_floor_kg=0.0003,
        ),
        "invertebrates": FoodLayerParameters(
            energy_density_eu_per_kg=21_000,
            growth_rate_per_tick=0.01,
            thermal_optimum_c=22,
            thermal_breadth_c=14,
            needs_light=False,
            diet_class="animal",
            handling_factor=0.3,
            digestion_rate_per_tick=0.50,
            max_assimilation=0.80,
            water_fraction=0.7,
            dispersal_rate=0.02,
            seed_floor_kg=0.0003,
        ),
        "algae": FoodLayerParameters(
            energy_density_eu_per_kg=14_000,
            growth_rate_per_tick=0.02,
            thermal_optimum_c=22,
            thermal_breadth_c=14,
            needs_light=True,
            diet_class="soft",
            handling_factor=0.6,
            digestion_rate_per_tick=0.40,
            max_assimilation=0.60,
            water_fraction=0.9,
            dispersal_rate=0.03,
            seed_floor_kg=0.0005,
        ),
        "fungi": FoodLayerParameters(
            energy_density_eu_per_kg=15_000,
            growth_rate_per_tick=0.01,
            thermal_optimum_c=16,
            thermal_breadth_c=16,
            needs_light=False,
            diet_class="soft",
            handling_factor=0.8,
            digestion_rate_per_tick=0.35,
            max_assimilation=0.60,
            water_fraction=0.85,
            dispersal_rate=0.01,
            seed_floor_kg=0.0003,
        ),
    }


class MeatParameters(FrozenModel):
    energy_density_eu_per_kg: float = 7_000.0
    handling_factor: float = 1.5
    digestion_rate_per_tick: float = 0.50
    max_assimilation: float = 0.85
    water_fraction: float = 0.65
    decay_rate_per_tick_at_20c: float = 0.019
    spoilage_rate_per_tick: float = 0.02
    spoilage_assimilation_penalty: float = 0.4
    spoilage_poisoning: float = 0.3
    decay_nutrient_per_kg: float = 0.01


class VegetationParameters(FrozenModel):
    initial_fraction_of_capacity: float = 0.7
    overshoot_fraction_of_capacity: float = 1.2
    burn_survival_fraction: float = 0.1
    min_canopy_share: float = 0.05
    moisture_half_saturation: float = 0.3
    light_half_saturation: float = 0.25
    nutrient_half_saturation: float = 0.2
    snow_access_scale_cm: float = 15.0
    fire_grass_flush_multiplier: float = 1.4
    trample_fraction_per_pass: float = 0.01
    trample_mass_threshold_kg: float = 100.0
    canopy_regrowth_per_tick: float = 0.002
    fire_canopy_survival: float = 0.3
    fruiting_peak_year_fraction: float = 0.55
    fruiting_width_year_fraction: float = 0.15
    fruiting_off_season_fraction: float = 0.2
    capacity_refresh_interval_ticks: int = 12


class HydrologyParameters(FrozenModel):
    snow_cm_per_mm: float = 1.0
    melt_cm_per_degree_tick: float = 0.4
    max_snow_cm: float = 300.0
    infiltration_per_mm: float = 0.025
    soil_drying_per_tick: float = 0.004
    heat_drying_per_10c: float = 0.4
    lake_recharge_per_tick: float = 0.002
    ponding_fraction: float = 0.5
    evaporation_m_per_tick_per_10c: float = 0.0004
    max_flood_above_base_m: float = 2.0
    litres_per_metre_of_patch_depth: float = 2_500_000.0


class NutrientParameters(FrozenModel):
    initial_level: float = 0.5
    weathering_per_tick: float = 0.0005
    leaching_rate_per_tick: float = 0.0002
    uptake_per_kg_growth: float = 0.02


class ToxinParameters(FrozenModel):
    diffusion: float = 0.1
    retention_per_tick: float = 0.97
    vent_emission_per_tick: float = 0.05


class ScentParameters(FrozenModel):
    diffusion: float = 0.2
    deep_water_decay_multiplier: float = 4.0
    shallow_water_decay_multiplier: float = 2.0
    rain_decay_multiplier: float = 2.0
    half_lives_ticks: dict[str, float] = Field(
        default_factory=lambda: {
            "fruit_aroma": 3.0,
            "carrion": 6.0,
            "blood": 2.0,
            "water": 12.0,
            "smoke": 2.0,
            "alarm_pheromone": 2.0,
            "estrus": 4.0,
            "musk": 4.0,
        }
    )
    musk_emission_per_kg075: float = 0.05
    carrion_emission_per_kg_decayed: float = 5.0
    blood_emission_per_damage: float = 20.0
    fruit_emission_per_kg: float = 0.5
    water_emission: float = 0.3
    estrus_emission: float = 2.0
    alarm_emission: float = 3.0
    smoke_emission_per_intensity: float = 5.0

    @field_validator("diffusion")
    @classmethod
    def _stable_diffusion(cls, value: float) -> float:
        if not 0.0 <= value <= 0.25:
            raise ValueError("explicit diffusion is only stable for 0 <= D <= 0.25")
        return value


class PerceptionParameters(FrozenModel):
    base_vision_radius: float = 3.0
    acuity_vision_radius: float = 9.0
    night_vision_compensation: float = 0.8
    detection_kappa: float = 6.0
    identification_threshold: float = 0.35
    naming_threshold: float = 0.7
    moving_detectability: float = 1.6
    still_detectability: float = 0.5
    ornament_detectability: float = 0.4
    crypsis_strength: float = 0.6
    scan_radius_bonus: float = 0.3
    scan_certainty_bonus: float = 0.2
    base_hearing_threshold_db: float = 40.0
    acuity_hearing_threshold_db: float = 30.0
    base_smell_threshold: float = 0.05
    olfaction_smell_range: float = 2.0
    hearing_attenuation_per_patch_db: float = 0.3
    storm_masking_db: float = 15.0
    wake_threshold_db: float = 25.0


class MemoryParameters(FrozenModel):
    min_spatial_slots: int = 4
    max_spatial_slots: int = 16
    min_social_slots: int = 3
    max_social_slots: int = 13
    min_half_life_ticks: float = 12.0
    max_half_life_ticks: float = 96.0
    episodic_slots: int = 5
    min_learning_rate: float = 0.05
    max_learning_rate: float = 0.6
    focus_learning_multiplier: float = 2.0
    habituation_rate: float = 0.1
    inherited_memories: int = 3


class CognitionParameters(FrozenModel):
    max_menu_options: int = 32
    salience_distance_weight: float = 1.0
    salience_danger_weight: float = 2.0
    salience_need_weight: float = 1.5
    salience_kin_weight: float = 1.0
    salience_novelty_weight: float = 0.5
    salience_approach_weight: float = 0.5
    min_attention_entities: int = 4
    max_attention_entities: int = 7
    max_smells: int = 3
    max_sounds: int = 3
    max_memories: int = 4
    max_state_tokens: int = 1500
    fear_integration_rate: float = 0.6
    min_decisiveness: float = 1.0
    max_decisiveness: float = 6.0
    hesitation_low_base: float = 0.25
    hesitation_high_base: float = 0.60
    hesitation_caution_span: float = 0.2
    urgent_threat_level: int = 3
    dithering_certainty_bonus: float = 0.15


class DevelopmentParameters(FrozenModel):
    diet_sharpness: float = 4.0
    armor_mass_gain: float = 0.3
    instinct_expression_threshold: float = 0.5
    strong_instinct_threshold: float = 0.75
    birth_mass_floor_kg: float = 0.02


class EvolutionParameters(FrozenModel):
    mutation_probability: float = 0.02
    mutation_sigma: float = 0.05
    large_mutation_fraction: float = 0.05
    large_mutation_sigma: float = 0.2
    linkage_switch_probability: float = 0.15
    developmental_noise: float = 0.03
    founder_allele_noise: float = 0.06
    species_distance: float = 0.15
    clustering_interval_ticks: int = 24
    species_min_members: int = 3
    species_persistence_rounds: int = 2


class EcologyParameters(FrozenModel):
    metabolism: MetabolismParameters = MetabolismParameters()
    thermal: ThermalParameters = ThermalParameters()
    water: WaterParameters = WaterParameters()
    digestion: DigestionParameters = DigestionParameters()
    sleep: SleepParameters = SleepParameters()
    stamina: StaminaParameters = StaminaParameters()
    health: HealthParameters = HealthParameters()
    aging: AgingParameters = AgingParameters()
    life_history: LifeHistoryParameters = LifeHistoryParameters()
    locomotion: LocomotionParameters = LocomotionParameters()
    combat: CombatParameters = CombatParameters()
    reproduction: ReproductionParameters = ReproductionParameters()
    disease: DiseaseParameters = DiseaseParameters()
    social: SocialParameters = SocialParameters()
    food_layers: dict[str, FoodLayerParameters] = Field(default_factory=default_food_layers)
    meat: MeatParameters = MeatParameters()
    vegetation: VegetationParameters = VegetationParameters()
    hydrology: HydrologyParameters = HydrologyParameters()
    nutrients: NutrientParameters = NutrientParameters()
    toxin: ToxinParameters = ToxinParameters()
    scent: ScentParameters = ScentParameters()
    perception: PerceptionParameters = PerceptionParameters()
    memory: MemoryParameters = MemoryParameters()
    cognition: CognitionParameters = CognitionParameters()
    development: DevelopmentParameters = DevelopmentParameters()
    evolution: EvolutionParameters = EvolutionParameters()
