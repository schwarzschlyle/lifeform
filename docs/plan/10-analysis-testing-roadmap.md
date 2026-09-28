# 10 — Analysis, Testing, Roadmap and Risks

---

## 10.1 Analyses (`lifeform.analysis`)

### Population and community

| Analysis | Method |
| --- | --- |
| Population dynamics | $N_s(t)$ per species; births and deaths by cause; per-capita growth rate $r(t)$ |
| Carrying capacity | Logistic fit $\dot N = rN(1 - N/K)$ per species (nonlinear least squares) |
| Predator–prey cycles | Lotka–Volterra parameter fit; cycle period from autocorrelation; phase portrait |
| Diversity | Species richness; Shannon $H' = -\sum p_i\ln p_i$; Simpson index |
| Trophic structure | Species classified by diet simplex; biomass per trophic level; Lindeman transfer efficiency |
| Food web | A directed graph built from kill and eat events: who eats whom, and how much |
| Life tables | $l_x$, $q_x$ and survivorship curves per species, classified as Type I, II or III |

### Evolution

| Analysis | Method |
| --- | --- |
| Trait trajectories | Mean and variance per species per 24-tick window, for every gene and derived phenotype |
| Selection differential | $S = \mathrm{Cov}(w, z)/\bar w$ with $w$ = lifetime reproductive success, per generation window |
| Price equation | $\Delta\bar z = \mathrm{Cov}(w, z)/\bar w + \mathrm{E}(w\,\Delta z)/\bar w$, separating selection from transmission bias (mutation, recombination) |
| Realized heritability | Parent–offspring regression |
| **Drift versus selection** | $Q_{ST}$ (trait loci) against $F_{ST}$ (neutral markers) between populations. $Q_{ST} > F_{ST}$ indicates divergent selection. This is the headline readout for The Sundering and Galápagos Scatter |
| Phylogeny | The species tree with branch lengths from neutral-marker distance; Newick export |
| Speciation tempo | Time to first speciation; speciation and extinction rates |

### Behavior (from the decision tape)

| Analysis | Method |
| --- | --- |
| Activity budgets | Share of time foraging, resting, vigilant, moving and social, by species, time of day and season (classic ethology) |
| Decision character | Confidence distributions; decisive, hesitant and dithering shares; exploratory rate (sampled ≠ argmax); effort distributions |
| **Fear calibration** | Jev's `threat` appraisal against realized predation risk in the next 3 ticks: are the animals appropriately afraid? |
| Learning curves | Confidence and success rate against age and experience |
| Personality effects | Does `boldness` predict `approach`, and does `sociability` predict `stay_with_group`? Mixed models by species |
| Kin effects | Alarm, sharing and defense rates as a function of relatedness (a test of Hamilton's rule) |

### Space

Home ranges (kernel density estimates), migration detection (displacement of the group centroid against the vegetation peak), a test of the ideal free distribution, and territory maps.

### Disease

Epidemic curves, a time-varying reproduction number $R_t$ estimated from infection trees, strain virulence trajectories, and mortality attributable to disease.

### Operations

Calls, tokens, cost and latency per world; 429 rate; retries; pause events.

---

## 10.2 The Chronicle (templated narrative, no LLM)

`ChronicleWriter` detects notable moments with rules and renders them from templates, with named individuals:

| Kind | Rule | Example line |
| --- | --- | --- |
| Firsts | First kill, birth or speciation of a world | "Day 3, dusk: Oru the Stripe Stalker made the first kill of the Serengeti, a young Meadow Grazer named Pell." |
| Records | Oldest individual, most offspring, largest herd, longest chase, longest migration | "Tamsi lived 2.4 years, longer than any grazer before her, and left 11 descendants." |
| Catastrophes | More than 20% of a species dying within one day | "The fire of late dry season, year 2, killed 14 animals in a single night." |
| Dynasties | The matriline with the most living descendants | "The line of Veli now numbers 23: one in four grazers descends from her." |
| Courage | A parent defended its young against a predator, and both survived | "Kesh stood over her calf as the pack closed in. Both lived." |
| Speciation and extinction | Registry events | "The island grazers have diverged: meet the Ashback Grazer." |

Every chronicle entry links to its tick and actors, so the theater can jump to it.

---

## 10.3 Testing strategy

| Level | Scope | Tools |
| --- | --- | --- |
| **Unit** | Every pure model: allometry, the Gompertz hazard, a diffusion step, Rescorla–Wagner, Elo, quantizers, conception and strike probabilities | pytest |
| **Property** | Torus distance is symmetric and ≤ half the width; diffusion conserves mass when decay is 0; occupancy never exceeds capacity; alleles stay in [0, 1]; energy only goes negative through the catabolism path; every menu contains the core set, has ≤ 32 options, and **every option passes an independent legality oracle** | hypothesis |
| **Golden** | `MindStateEncoder` output for fixture organisms; `PanelCodec` SDK payloads; manifest schema | Snapshot files |
| **Contract** | `PanelCodec.decode` against recorded `SystemOneResponse` JSON; `live`-marked tests against the real API (3 scenarios, skipped without `TYPESAFE_API_KEY`) | pytest markers |
| **Scenario** | A predator chase resolves correctly; courtship → conception → birth → nursing → weaning; fire spread and flight; flood drowning; SEIR in a closed group; speciation clustering on synthetic genomes | `ScriptedBrain` |
| **Determinism** | 100 ticks with `ScriptedBrain` run twice give identical bundle hashes. 30 ticks with `JevBrain`, then `lifeform resimulate` with `TapeBrain`, give identical frames | CI |
| **Behavioral** | The Question Lab suites ([07 §7.11](07-jev-nervous-system.md)) | Nightly with a live key |
| **Performance** | Tick CPU time (excluding the brain) ≤ 50 ms at 300 organisms on 192²; field phases ≤ 30 ms | pytest-benchmark |
| **Web** | Decoders, the interpolator and the playback clock; Playwright visual smoke tests on a fixture bundle at fixed ticks (with pixel tolerance) | vitest, Playwright |

**CI** (GitHub Actions): ruff, mypy strict, and all offline test levels on Python 3.12–3.14; web lint, typecheck, tests and build. A nightly job runs the Question Lab and live contract tests using a repository secret.

---

## 10.4 Roadmap

Durations assume one developer working with AI assistance. Every milestone has an exit criterion.

| Milestone | Weeks | Deliverables | Exit criterion |
| --- | --- | --- | --- |
| **M0 · Foundations and Jev probe** | 1 | Repository, tooling, config models, `JevGateway`, `RateGovernor`, `PanelCodec`, `lifeform preflight`, a Question Lab harness with 20 seed scenarios | p50 and p95 latency and token sizes measured. **Temperament-sensitivity gate (suite 4) passed**, or its escalation path chosen |
| **M1 · World substrate** | 2–3 | Grid, generation, climate, hydrology, production, diffusion, sound, disturbances; a prototype terrain shader to inspect worlds visually | All 12 presets generate; field phases ≤ 30 ms per tick |
| **M2 · Organism core** | 3–4 | Genome, inheritance, development, physiology models, drives, conditions, mortality | Energy, water, thermal and aging scenario tests pass |
| **M3 · Perception and mind** | 4–5 | Senses, line of sight, salience, memory, learning, vocabulary, relational facts, affordances, encoder, panel | Golden tests; token p95 ≤ 1,500; Lab suite 1 ≥ 85% |
| **M4 · Actions and ecology** | 5–7 | All resolvers, the sub-step mover, predation, reproduction, disease, social rules | Scenario tests; a **60-tick smoke run with real Jev** completes |
| **M5 · Recording and theater MVP** | 7–9 | Bundle writer, server, `ReplayStore`, terrain and creature layers, timeline, mind inspector | The smoke run replays at 60 fps; the inspector shows real decisions |
| **M6 · Evolution and analysis** | 9–10 | Speciation, phylogeny, stats, charts, chronicle | A Red Queen Pit preview shows cycles and a phylogeny |
| **M7 · Calibration and presets** | 10–12 | `lifeform calibrate`; pilots and calibration for all 12 worlds; a full `preview` run (about $10) | Every world holds populations in band for 300 ticks with no ceiling hits or collapse |
| **M8 · Aesthetic polish** | 12–13 | Weather and lighting shaders, creature detail, effects, Cinematic Director, highlight reel, optional sound, clip export | Visual review sign-off |
| **M9 · The big run** | 14 | The `standard` run across 12 worlds (about 22 h, about $87); a findings report per world against its hypotheses | Report published |

---

## 10.5 Risks and mitigations

| Risk | Likelihood | Impact | Mitigation |
| --- | --- | --- | --- |
| Rate limits tighten, or vary ("adjusting dynamically") | Medium | High | AIMD governor; `estimate` before runs; `preview` profile; request a higher tier |
| **Jev is insensitive to temperament and instinct text** | Medium | High | Lab suite 4 gate at M0; escalation path ([07 §7.11](07-jev-nervous-system.md)); morphology, sensory and sampling genes still evolve regardless |
| Jev choices are generic (for example resting too often) | Medium | Medium | Relational facts (J3); consequence-bearing option descriptions; wording A/B; activity-budget monitoring |
| Positional bias in menus | Low–Medium | Medium | Per-call shuffling; Lab suite 3 |
| Model version drift | Medium | Medium | Pinned model; `response.model` logged; Lab regression on change |
| Population explosion or collapse | High early | High | Calibration protocol; refugia in presets; pause at the population ceiling; preview runs first |
| Too few generations for visible evolution | Medium | Medium | Compressed calendar; fast-breeding archetypes; the long Red Queen run; `deep-evolution` profile; evolvable mutation rate |
| Emergent exploits (for example hiding forever) | Medium | Low | Every behavior has a metabolic or opportunity cost; activity budgets are monitored |
| Replay bundles too large | Low | Low | Chunking, XOR deltas, decision-detail levels |
| Cost overrun | Low | Medium | `BudgetGuard` hard stop at a checkpoint |
| Non-reproducibility | Low | Medium | Decision tape plus `TapeBrain` |
| Frontend performance | Low | Medium | Budgets in [09 §9.11](09-replay-and-visualization.md); batched rendering; worker decoding |
| Scope creep | High | Medium | Exit criteria per milestone; stretch worlds deferred |

---

## 10.6 Open questions for the user

1. **API tier:** will runs use a standard key (1,200 RPM) or a higher-limit tier? This decides whether the standard profile takes about 22 hours or a few.
2. **Budget:** is about $87 (about 22 h) acceptable for the full standard run, after a $10 preview?
3. **Priorities:** if trimming is needed, which worlds matter most?
4. **Code-style reading:** the plan reads "avoid writing inline codes" as *no inline comments and no hard-coded values in logic: self-documenting names, typed parameter objects, small classes*. Is that the intent?
5. **Hosting:** is the theater local-only, or should it be published (for example as a static site with sample bundles)?
6. **Sound:** keep the optional ambient audio in the theater, or drop it?

---

## 10.7 Glossary

| Term | Meaning |
| --- | --- |
| **Tick** | One discrete time step (2 simulated hours) and one decision per organism |
| **Patch** | One grid cell |
| **Mind state** | The words-only JSON sent to Jev as `state` |
| **Question panel** | The 5 typed questions sent with every mind state |
| **Affordance / menu** | A legal, grounded option (verb × target) / the set of options offered in one call |
| **Band** | Execution mode set by confidence: decisive, hesitant or dithering |
| **Decisiveness β** | Heritable exponent that sharpens Jev's action distribution before sampling |
| **Run bundle** | Everything a run recorded, as consumed by the theater |
| **Decision tape** | Every call's state, menu, answers and metadata |
| **Question Lab** | The behavioral test harness for Jev wording and sensitivity |
| **Archetype / preset** | A founder genome template / a world configuration |
| **PAL** | Physical activity level (multiple of basal metabolism) |
| **EU** | Energy unit (nominally 1 kJ) |
| **RHP** | Resource-holding potential (contest strength) |
| **SEIR** | Susceptible, exposed, infectious, recovered (disease states) |
| **$\delta$, $\delta_{iso}$, $\delta_{sp}$** | Genetic distance, the isolation threshold and the species-clustering threshold |
