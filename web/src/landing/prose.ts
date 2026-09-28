export interface Titled {
  title: string;
  text: string;
}

export interface WeaknessResponse {
  weakness: string;
  response: string;
}

export interface DesignRule {
  code: string;
  rule: string;
  detail: string;
}

export interface CommandStep {
  command: string;
  explanation: string;
}

export const HERO_TAGLINE =
  "Artificial ecologies on fourteen worlds. Code runs the physics, bodies and genes. Every choice any animal makes "
  + "comes from Jev: one call per animal, every two simulated hours.";

export const JEV_INTRODUCTION = [
  "Jev is TypeSafe AI's first System One model, released in September 2026. It is named after the economist William "
  + "Stanley Jevons. \"System One\" is Daniel Kahneman's term for fast, intuitive judgment, as opposed to slow, "
  + "deliberate reasoning.",
  "Jev does not write text. You send it a state, which is a description of a situation, and a set of typed questions. "
  + "It returns calibrated answers: a choice with the probability of every option, or an expected level on a "
  + "described scale. All the questions in one request are answered independently, against the same state, in a "
  + "single round trip.",
  "That is the shape of a nervous system. One moment of experience, several judgments at once (what to do, how "
  + "dangerous this is, how hard to try), and some judgments much clearer than others. Lifeform uses Jev as the "
  + "nervous system of every simulated animal.",
];

export const QUESTION_TYPES: Titled[] = [
  {
    title: "Choice",
    text: "Pick one of many labelled options. Returns the choice, a confidence from 0 (a flat guess) to 1 (certain) "
      + "and the probability of every option.",
  },
  {
    title: "Score",
    text: "Rate the situation on an ordered scale of described levels. Returns the expected level and the "
      + "probability of each level.",
  },
  {
    title: "Noul",
    text: "Yes or no. Returns the probability of yes. Lifeform does not use it.",
  },
];

export const VENDOR_FACTS: [string, string][] = [
  ["Typical latency", "about 100 ms per call (vendor-reported)"],
  ["Context", "64k tokens per request"],
  ["Input", "text only; English works best"],
  ["Output guarantee", "answers always match the declared type (vendor-reported)"],
  ["Customization", "none: the same weights for everyone; only the wording changes"],
];

export const JEV_WEAKNESSES: WeaknessResponse[] = [
  {
    weakness: "It cannot count or do arithmetic. Numbers are read as text, not quantities.",
    response: "No number ever reaches Jev. Code turns every quantity into words: \"very hungry\", \"twice your "
      + "size\", \"mid-distance to the south-west\", \"seen yesterday\".",
  },
  {
    weakness: "It reads literally. Negations and implied conditions are taken at face value.",
    response: "Questions and options are worded positively and atomically. Each option states its own consequence.",
  },
  {
    weakness: "Irrelevant context lowers accuracy.",
    response: "A salience ranker keeps only the few things that matter most to this animal right now.",
  },
  {
    weakness: "It cannot infer facts the state does not contain.",
    response: "Code works out relational facts and states them plainly: \"it is faster than you\", \"it has not "
      + "noticed you\", \"deep water lies between you\".",
  },
  {
    weakness: "Answers to separate questions are not forced to agree.",
    response: "Each answer has its own job. Nothing assumes the chosen action and the danger rating agree.",
  },
  {
    weakness: "An unpinned model can drift between versions.",
    response: "The model version is pinned, and the version that answered is recorded with every decision.",
  },
];

export const CODE_DUTIES = [
  "Terrain, climate, weather, water, plants, fire, floods and eruptions",
  "Senses: what each animal can see, smell and hear, and what it remembers",
  "Which actions are physically possible right now (the menu)",
  "Movement, pursuit, strikes, wounds, eating, digestion and mating",
  "Metabolism, body temperature, thirst, growth, aging and disease",
  "Genes, inheritance, mutation and the detection of new species",
];

export const JEV_DUTIES = [
  "Which action to take next, out of the legal menu",
  "How much effort the moment deserves",
  "How much danger the animal is in",
  "Which call, if any, to make",
  "Which single thing to pay attention to",
];

export const PIPELINE_STEPS: Titled[] = [
  { title: "Body and world", text: "Code updates every field, body and relationship." },
  { title: "Perception", text: "Each animal senses its surroundings. A salience ranker keeps what matters." },
  { title: "State in words", text: "Its experience is written as words only: no numbers, no coordinates." },
  { title: "Jev", text: "One call answers five questions at once." },
  { title: "Interpretation", text: "Probabilities become an intention, shaped by the animal's own genes." },
  { title: "Physics", text: "Code carries out the intention and works out what happens." },
];

export const DESIGN_RULES: DesignRule[] = [
  { code: "J1", rule: "One call per animal per tick", detail: "All five questions ride in that single call." },
  { code: "J2", rule: "Words, not numbers", detail: "Quantities become graded words before Jev sees them." },
  { code: "J3", rule: "The state contains the answer", detail: "Code states the relational facts an animal would just know." },
  { code: "J4", rule: "Small, salient state", detail: "About 600–900 tokens, chosen by salience." },
  { code: "J5", rule: "Grounded, legal options", detail: "Only actions possible right now are offered." },
  { code: "J6", rule: "Positive, literal wording", detail: "Explicit \"none\" options where nothing is a valid answer." },
  { code: "J7", rule: "Pin the model", detail: "Every decision records the version that answered." },
  { code: "J8", rule: "Use the whole distribution", detail: "Actions are sampled from Jev's probabilities." },
  { code: "J9", rule: "Throughput is the limit", detail: "One rate governor shares the request budget across worlds." },
  { code: "J10", rule: "Record everything", detail: "Replays read the tape. They never call Jev again." },
  { code: "J11", rule: "Independent answers", detail: "No logic assumes two answers agree." },
  { code: "J12", rule: "Code never chooses", detail: "A failed call is retried and the tick waits. Nothing is substituted." },
];

export const WORLD_MECHANICS: Titled[] = [
  {
    title: "A seamless torus",
    text: "Every world is a grid of patches that wraps at the edges, so there are no borders to hide behind. "
      + "Animals move in eight directions.",
  },
  {
    title: "Climate and weather",
    text: "Temperature follows latitude, season, time of day, altitude and terrain. Each world has its own weather "
      + "profile: rain, fog, storms, a moving rain belt, or permanent day and night on a tidally locked ring.",
  },
  {
    title: "Water",
    text: "Rivers, lakes and the sea are drinkable in shallow patches. Deep water drowns animals that cannot swim. "
      + "Floods and droughts change where water is.",
  },
  {
    title: "Plants",
    text: "Seven food layers regrow each tick at a rate set by temperature, light and moisture, and spread slowly "
      + "into neighboring patches. Snow buries ground food. Grazed land recovers from what remains.",
  },
  {
    title: "Scent and sound",
    text: "Musk, carrion, blood, ripe fruit, water, smoke and alarm scents spread, fade and drift with the wind. "
      + "Calls have a loudness in decibels that falls with distance, and each animal's hearing decides what it hears.",
  },
  {
    title: "Disturbances",
    text: "Wildfire, floods, droughts, volcanic eruptions, a continental rift, rafting between islands, epidemics "
      + "and slow climate drift. Each world has its own mix.",
  },
];

export const ECOLOGY_MODELS: Titled[] = [
  {
    title: "Kleiber's law",
    text: "Basal energy use scales with body mass to the ¾ power. Bite size, milk supply and feeding priority "
      + "scale the same way, so size matters without being everything.",
  },
  {
    title: "Heat balance",
    text: "Heat leaks through the skin at a rate that grows more slowly with body size than metabolism does, and "
      + "insulation cuts it further, so big animals keep warm cheaply. Warm-blooded animals burn energy to hold "
      + "37.5 °C; cold-blooded ones track the air and bask.",
  },
  {
    title: "Q10 temperature scaling",
    text: "Cold-blooded bodies and rotting carcasses both run 2.5× faster for every 10 °C of warmth.",
  },
  {
    title: "Ontogenetic growth",
    text: "Young grow along a West-style curve: fast at first, slowing as they approach adult size. Growth needs "
      + "surplus energy, so hungry young stay small.",
  },
  {
    title: "Gompertz–Makeham aging",
    text: "The risk of dying of old age rises exponentially with age relative to life span, on top of a small "
      + "constant background risk.",
  },
  {
    title: "Epidemics with evolving strains",
    text: "Infections move from exposed to infectious to recovered. Strains mutate as they spread, and each can only "
      + "infect hosts genetically close to the host it came from.",
  },
  {
    title: "Associative learning",
    text: "Rescorla–Wagner updates: each experience nudges what an animal associates with a species or place, by its "
      + "learning rate times how striking the experience was.",
  },
  {
    title: "Elo dominance",
    text: "Contests within a species update Elo ratings. The ratings decide who feeds first at a shared carcass.",
  },
  {
    title: "Diploid genetics",
    text: "Two copies of every locus. Each parent passes one copy of each, with mutation. Heritable variation is what "
      + "selection works on.",
  },
];

export const RUN_STEPS: CommandStep[] = [
  { command: "lifeform worlds", explanation: "List the 14 world presets." },
  { command: "lifeform brain kev", explanation: "Make Kev the default brain; lifeform brain jev switches back." },
  { command: "lifeform estimate serengeti-pulse --ticks 300", explanation: "See calls, cost and wall time first." },
  { command: "lifeform preflight", explanation: "Check the API key, the pinned model and one call's latency." },
  {
    command: "lifeform run serengeti-pulse --ticks 300 --population-scale 0.5 --max-usd 2",
    explanation: "Shows the estimate and asks before spending. The key is typed in hidden and never saved.",
  },
  { command: "lifeform serve", explanation: "Open this theater at http://127.0.0.1:8765." },
];

export const BRAIN_SWITCH_NOTES = [
  "Lifeform talks to its brain through TypeSafe's System One protocol, and Kev, an open Jev-style model you host "
  + "yourself, speaks the same protocol. Switching changes only where the calls go: every animal still gets exactly "
  + "one call per tick with the same five questions, and replays record which brain answered.",
  "Kev is not Jev. It was trained on shorter texts than the 600–900-token states Lifeform sends, so expect weaker "
  + "judgment, especially from the smaller Kevs; Kev-27B holds up best on long inputs. Runs are labelled with the "
  + "brain that made them, so results from the two are never mixed up.",
];

export const DIET_COLORS: Record<string, string> = {
  fiber: "#7fbf5a",
  soft: "#f2c14e",
  animal: "#e5604f",
};

export const DIET_LABELS: Record<string, string> = {
  fiber: "grass, leaves, twigs",
  soft: "fruit, seeds, algae, fungi",
  animal: "meat, grubs, carrion",
};

export const FAMILY_TITLES: Record<string, string> = {
  locomotion: "Moving",
  foraging: "Eating and drinking",
  combat: "Fighting",
  concealment: "Hiding",
  body_care: "Body care",
  social: "Social",
  reproduction: "Reproduction",
};
