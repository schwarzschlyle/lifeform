import type { DecisionRecord } from "./types";

export interface JevFacts {
  maker: string;
  model: string;
  requests_per_minute: number;
  tokens_per_second: number;
  price_usd_per_million_input_tokens: number;
  tokens_per_call: number;
  questions_per_call: number;
}

export interface BrainFacts {
  name: string;
  title: string;
  description: string;
  model: string;
  endpoint: string;
  price_usd_per_million_input_tokens: number;
  host_usd_per_hour: number;
  requests_per_minute: number;
}

export interface BrainRegistryFacts {
  active: string;
  providers: BrainFacts[];
}

export interface PanelQuestion {
  key: string;
  type: "Choice" | "Score";
  instructions: string;
  answers: string[];
}

export interface Interpretation {
  min_decisiveness: number;
  max_decisiveness: number;
  hesitant_below: number;
  dithering_below: number;
  caution_span: number;
  urgent_threat_level: string;
  fear_integration_rate: number;
  max_state_tokens: number;
  attention: { entities: number; smells: number; sounds: number; memories: number };
}

export interface PanelFacts {
  version: string;
  max_menu_options: number;
  interpretation: Interpretation;
  questions: PanelQuestion[];
}

export interface CalendarFacts {
  ticks_per_day: number;
  hours_per_tick: number;
  days_per_season: number;
  ticks_per_year: number;
}

export interface NamedNote {
  name: string;
  note: string;
}

export interface GeneModuleFacts extends NamedNote {
  count: number;
}

export interface GeneReference {
  index: number;
  name: string;
  module: string;
  low: number;
  high: number;
  scale: "linear" | "log";
  unit: string;
  note: string;
}

export interface InstinctFacts {
  key: string;
  wording: string;
}

export interface VerbFacts {
  name: string;
  family: string;
  pal: number;
  moves: boolean;
  note: string;
}

export interface CallFacts {
  name: string;
  description: string;
  level_db: number;
  adults_only: boolean;
  min_vocal_capacity: number;
}

export interface TerrainFacts {
  id: number;
  name: string;
  description: string;
  move_cost: number | null;
  cover: number;
  sight_opacity: number;
  temperature_offset_c: number;
  food: Record<string, number>;
}

export interface FoodLayerFacts {
  key: string;
  energy_density_eu_per_kg: number;
  growth_rate_per_tick: number;
  thermal_optimum_c: number;
  thermal_breadth_c: number;
  needs_light: boolean;
  diet_class: string;
  digestion_rate_per_tick: number;
  max_assimilation: number;
  water_fraction: number;
}

export interface Diet {
  fiber: number;
  soft: number;
  animal: number;
}

export interface SpeciesStats {
  adult_mass_kg: number;
  lifespan_days: number;
  maturity_days: number;
  gestation_days: number;
  weaning_days: number;
  litter_size: number;
  top_speed_patches_per_tick: number;
  basal_energy_per_tick: number;
  fasting_days: number;
  stomach_kg: number;
  bite_kg: number;
  vision_day_patches: number;
  vision_night_patches: number;
  hearing_threshold_db: number;
  attack_power: number;
  defense: number;
  warm_blooded: boolean;
  comfortable_down_to_c: number | null;
  decisiveness_beta: number;
  caution: number;
  thermal_optimum_c: number;
  thermal_breadth_c: number;
}

export interface GeneValue {
  name: string;
  module: string;
  fraction: number;
  value: number;
  unit: string;
}

export interface Appearance {
  world: string;
  slug: string;
  count: number;
  local_name: string | null;
  overrides: Record<string, number>;
}

export interface ArchetypeFacts {
  slug: string;
  name: string;
  summary: string;
  hue: number;
  diet: Diet;
  temperament: string[];
  rhythm: string;
  instincts: (InstinctFacts & { strength: number })[];
  stats: SpeciesStats;
  genes: GeneValue[];
  worlds: Appearance[];
}

export interface FounderGroup {
  archetype: string;
  name: string | null;
  count: number;
  groups: number;
  overrides: Record<string, number>;
}

export interface WorldFacts {
  slug: string;
  title: string;
  biome: string;
  description: string;
  question: string;
  palette: string;
  stretch: boolean;
  grid: [number, number];
  default_ticks: number;
  seasons: string[];
  climate: {
    equator_temperature_c: number;
    seasonal_amplitude_c: number;
    diurnal_amplitude_c: number;
    weather: string;
    tidally_locked: boolean;
    moving_rain_belt: boolean;
  };
  water_fraction: number;
  features: string[];
  disturbances: string[];
  founders: FounderGroup[];
  targets: { herbivores: number; predators: number; max_population: number };
}

export interface ProjectCatalog {
  jev: JevFacts;
  brains: BrainRegistryFacts;
  panel: PanelFacts;
  calendar: CalendarFacts;
  phases: NamedNote[];
  modules: GeneModuleFacts[];
  genes: GeneReference[];
  instincts: InstinctFacts[];
  verbs: VerbFacts[];
  calls: CallFacts[];
  terrain: TerrainFacts[];
  food_layers: FoodLayerFacts[];
  death_causes: NamedNote[];
  archetypes: ArchetypeFacts[];
  worlds: WorldFacts[];
}

export interface DecisionSample {
  tick: number;
  decision: DecisionRecord;
}
