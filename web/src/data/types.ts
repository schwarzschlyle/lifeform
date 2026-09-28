export interface RunWorldEntry {
  slug: string;
  title: string;
  biome: string;
  palette: string;
  status: string;
  ticks?: number;
  population?: number;
  calls?: number;
}

export interface RunManifest {
  run_id: string;
  label: string;
  status: string;
  created: string;
  brain: string;
  brain_title?: string;
  is_jev: boolean;
  model: string;
  served_model?: string;
  totals: { calls: number; tokens: number; usd: number };
  worlds: RunWorldEntry[];
}

export interface TerrainTypeInfo {
  id: number;
  name: string;
  description: string;
}

export interface WorldMeta {
  slug: string;
  title: string;
  biome: string;
  description: string;
  question: string;
  palette: string;
  tidally_locked: boolean;
  width: number;
  height: number;
  ticks_completed: number;
  status: string;
  brain: string;
  calls: number;
  tokens: number;
  calendar: { ticks_per_day: number; ticks_per_season: number; season_names: string[] };
  field_scales: Record<string, number>;
  terrain_types: TerrainTypeInfo[];
  food_layers: string[];
  verbs: string[];
  call_names: string[];
  conditions: string[];
  death_causes: string[];
  population: number;
}

export type ChunkRange = [number, number, string];

export interface BundleIndex {
  frames: ChunkRange[];
  fields: ChunkRange[];
  decisions: ChunkRange[];
  chunk_ticks: number;
  keyframe_interval: number;
}

export interface StaticData {
  width: number;
  height: number;
  terrain: Uint8Array;
  elevation: Uint8Array;
  elevation_max_m: number;
  substellar: Uint8Array;
}

export interface Clock {
  tick_of_day: number;
  day: number;
  season: number;
  season_word: string;
  phase: string;
  light: number;
  sun: number;
  weather: number;
  wind: [number, number];
  temperature: number;
}

export interface OrganismColumns {
  id: number[];
  species: number[];
  x: number[];
  y: number[];
  heading: number[];
  verb: number[];
  target: number[];
  effort: number[];
  band: number[];
  call: number[];
  confidence: number[];
  energy: number[];
  hydration: number[];
  health: number[];
  fear: number[];
  sleep: number[];
  mass: number[];
  flags: number[];
  outcome: number[];
  sex: number[];
  age: number[];
}

export interface Frame {
  tick: number;
  clock: Clock;
  organisms: OrganismColumns;
  paths: Record<string, number[]>;
}

export interface FieldKeyframe {
  tick: number;
  layers: Record<string, Uint8Array>;
}

export interface EventRecord {
  tick: number;
  kind: string;
  actors: number[];
  position: [number, number] | null;
  payload: Record<string, unknown>;
}

export interface OrganismSummary {
  id: number;
  name: string;
  species: number;
  species_name: string;
  sex: string;
  birth_tick: number;
  death_tick: number | null;
  death_cause: string | null;
  mother: number | null;
  father: number | null;
  generation: number;
  archetype: string | null;
  adult_mass_kg: number;
  diet: [number, number, number];
  traits: Record<string, number>;
  instincts: string[];
  offspring: number;
}

export interface SpeciesEntry {
  id: number;
  name: string;
  parent: number | null;
  origin_tick: number;
  extinct_tick: number | null;
  hue: number;
  archetype: string | null;
  peak_population: number;
  history: [number, number][];
}

export interface StatsRow {
  tick: number;
  population: Record<string, number>;
  births: number;
  deaths: Record<string, number>;
  bands: Record<string, number>;
  verbs: Record<string, number>;
  calls: number;
  tokens: number;
  vegetation: Record<string, number>;
  carcasses: number;
  traits?: Record<string, Record<string, number>>;
}

export interface ChoiceAnswer {
  choice: string;
  confidence?: number;
  probabilities: Record<string, number>;
}

export interface ScoreAnswer {
  score: number;
  probabilities: Record<string, number>;
}

export interface DecisionRecord {
  id: number;
  menu: [string, string][];
  answers: {
    action: ChoiceAnswer;
    effort: ScoreAnswer;
    threat: ScoreAnswer;
    call: ChoiceAnswer;
    focus: ChoiceAnswer;
  };
  sampled: string;
  argmax: string;
  band: string;
  effort: number;
  urgent: boolean;
  call: string;
  focus: string | null;
  outcome: string | null;
  model: string;
  tokens: number;
  latency_ms: number;
  attempts: number;
  state?: Record<string, unknown>;
}
