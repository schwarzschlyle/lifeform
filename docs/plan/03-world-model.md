# 03 — World Model

The world is the part of Lifeform that is **pure code and mathematics**: space, time, terrain, climate, water, plants, chemistry, sound and disturbances. Organisms live in it and change it. They eat, drink, trample, die and decompose, but they never *compute* it.

---

## 3.1 Space

| Property | Decision |
| --- | --- |
| Topology | **2D torus**: walking off one edge enters the opposite edge, so there are no arbitrary walls |
| Grid | Square cells called **patches**; per-preset size from 96×96 to 224×224; **default 160×160** |
| Why not always 256×256 | Jev throughput supports about 100 decision-makers per world. At 256² that is about 1 animal per 650 patches, so encounters (predation, mating, herding) become rare. 160² gives about 1 per 250 patches with vision radii of 4–12. Presets can still choose 256² for sparse, migratory worlds |
| Neighborhood | 8-connected (Moore) for movement; direction words N, NE, E, SE, S, SW, W, NW |
| Movement metric | Toroidal Chebyshev steps. Diagonal steps cost $\sqrt 2$ in energy |
| Sensing metric | Toroidal Euclidean: $d = \sqrt{\Delta x^2 + \Delta y^2}$ with $\Delta x = \min(\lvert x_1-x_2\rvert,\ W-\lvert x_1-x_2\rvert)$ |
| Patch scale | Nominally about 50 m: the scale at which an animal interacts with food, water and neighbors |
| Occupancy | Each patch holds **1.0 body unit**. An organism occupies $u = \mathrm{clip}(M / M_{ref}, 0.1, 1.0)$ with $M_{ref} = 20$ kg, so several small animals can share a patch but two large ones cannot. Dependent young share with their mother for free |

**Seamless tiling:** every noise field is sampled from **4D OpenSimplex noise on a torus embedding**, $(x, y) \mapsto (\cos\tfrac{2\pi x}{W}, \sin\tfrac{2\pi x}{W}, \cos\tfrac{2\pi y}{H}, \sin\tfrac{2\pi y}{H})$. There are no seams in terrain, weather or plants.

---

## 3.2 Time

| Unit | Default | Configurable | Notes |
| --- | --- | --- | --- |
| **Tick** | 2 simulated hours: one behavioral bout, one decision | yes | Every living organism gets one Jev call per tick |
| Day | **12 ticks** | `ticks_per_day` | Named day phases are used in the state (below) |
| Season | 12 days = 144 ticks | `days_per_season` | Compressed calendar |
| Year | 4 seasons = **576 ticks** | — | |
| Lunar cycle | 8 days = 96 ticks | `days_per_lunar_cycle` | Night light for nocturnal species |

**The calendar is compressed on purpose.** Real seasons last about 90 days. Here they last 12, so a `standard` run of 1,500 ticks covers about 2.6 years and **5–10 generations** of fast-breeding species. Life-history durations (maturity, gestation, lifespan) are scaled with the calendar so their *ratios* stay biologically plausible (see [04 §4.5](04-organism-model.md)).

**Day-phase words given to Jev** (tick of day → word): 0 `midnight`, 1 `deep night`, 2 `before dawn`, 3 `dawn`, 4 `morning`, 5 `late morning`, 6 `midday`, 7 `afternoon`, 8 `late afternoon`, 9 `dusk`, 10 `evening`, 11 `night`.

**Season words:** `early/mid/late` + `spring/summer/autumn/winter`, or `wet season` / `dry season` in tropical presets.

---

## 3.3 Terrain

There are thirteen terrain types. Terrain is mostly static but can change through disturbances (fire lowers canopy, eruptions create volcanic ground, rifts create water, glaciation brings ice cover).

| Id | Terrain | Move cost (walker) | Swimmer | Cover | Sight opacity per patch | Diurnal damping | Main food layers (K in kg/patch before productivity scaling) | Special |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 0 | Deep water | impassable | 1.0 | 0.1 | 0.0 | 0.8 | algae 2 | Drowning for non-swimmers; scent decays 4× faster |
| 1 | Shallow water | 2.0 (wading) | 0.8 | 0.2 | 0.0 | 0.6 | algae 3, invertebrates 2 | Drinkable; wallowing; breaks scent trails |
| 2 | Beach / sand | 1.3 | — | 0.0 | 0.0 | 0.2 | invertebrates 1, seeds 0.5 | Easy digging |
| 3 | Grassland | 1.0 | — | 0.1 | 0.02 | 0.0 | grass 8, seeds 2, invertebrates 1 | Fire-prone when dry |
| 4 | Savanna / shrubland | 1.1 | — | 0.25 | 0.05 | 0.1 | grass 6, browse 3, seeds 2 | Fire-prone |
| 5 | Forest (temperate / boreal) | 1.4 | — | 0.5 | 0.20 | 0.4 | browse 6, fruit 3, invertebrates 3, fungi 1 | Climbing; shade |
| 6 | Rainforest | 1.7 | — | 0.8 | 0.35 | 0.6 | fruit 8, browse 5, invertebrates 5, fungi 2 | Low light at the floor |
| 7 | Wetland / marsh | 1.6 | 0.5 | 0.4 | 0.10 | 0.5 | grass 5, algae 3, invertebrates 4 | Mud; environmental pathogen persists 2× longer |
| 8 | Desert | 1.2 | — | 0.05 | 0.0 | −0.3 (amplifies) | seeds 1.5, invertebrates 0.5 | Extreme diurnal swing; easy burrowing |
| 9 | Tundra | 1.5 (+ snow) | — | 0.05 | 0.0 | 0.1 | grass (lichen) 2, invertebrates 0.3 | Snowpack covers food |
| 10 | Rock / mountain | 2.2; cliff impassable if slope > 35° | — | 0.4 (crevices) | 1.0 if higher than viewer | 0.2 | seeds 0.5, grass 1 | High elevation is cold |
| 11 | Volcanic | 1.3 | — | 0.2 | 0.05 | 0.3 | fungi 1 | Toxin emission; geothermal +8 °C |
| 12 | Cave | 1.5 | — | 0.9 | 0.9 | 0.95 | fungi 4, invertebrates 3 | Light = 0; temperature is stable at the local annual mean |

Snow adds movement cost $+\ 0.02 \cdot \text{depth}_{cm}$, and hides ground food from grazers: accessible fraction $= e^{-\text{depth}/15\,\text{cm}}$.

---

## 3.4 Per-patch fields

All fields are `float32` numpy arrays of shape `(H, W)` unless noted.

| Field | Unit / range | Static? | Updated by |
| --- | --- | --- | --- |
| `elevation` | m | mostly | generation, eruption, rift |
| `terrain` | `uint8` id | mostly | generation, disturbances |
| `canopy` | 0–1 | dynamic | logistic regrowth, fire, browsing damage |
| `temperature` | °C | dynamic | climate |
| `light` | 0–1 | dynamic | sun, moon, clouds, canopy |
| `precipitation` | mm/tick | dynamic | weather cells |
| `soil_moisture` | 0–1 | dynamic | bucket model |
| `surface_water` | depth in m | dynamic | lakes, rivers, rain, evaporation, floods, drinking |
| `snow_depth` | cm | dynamic | snowfall, melt |
| `food[layer]` | kg/patch, 7 layers: grass, browse, fruit, seeds, invertebrates, algae, fungi | dynamic | production, consumption, fire |
| `soil_nutrients` | 0–1 | dynamic | decomposition, excretion, uptake, leaching |
| `toxin` | 0–1 | dynamic | vents, eruptions, diffusion, decay |
| `pathogen[strain]` | 0–1, up to 4 strains | dynamic | shedding, decay, diffusion in water |
| `fire` | intensity 0–1 | dynamic | fire cellular automaton |
| `burn_age` | ticks since fire | dynamic | fire |
| `scent[channel]` | concentration 0–∞ | dynamic | diffusion–decay–advection |
| `wind` | global vector + local noise | dynamic | climate |

**Entities** are stored in a spatial hash (`EntityIndex`) rather than as fields:

- `Carcass` (mass, species of origin, age, spoilage, infection);
- `Den` (owner, kind: burrow, nest, den; quality);
- `FoodCache` (owner, food layer, mass);
- `TerritoryMark` (owner, species, strength, age).

---

## 3.5 World generation (`WorldBuilder`)

These stages are run in order. Every stage is a class with its own parameters from the preset.

1. **Elevation** (`ElevationBuilder`): fBm of torus-embedded 4D OpenSimplex noise, with 5–7 octaves, persistence 0.5 and lacunarity 2. Optional ridged noise makes mountain chains. Presets may add stamps: island masks, calderas, rift valleys and plateau shelves.
2. **Sea level** (`SeaLevel`): sea level is set at the preset's water-fraction percentile (for example 0.70 for the archipelago, 0.05 for the desert).
3. **Depression filling and lakes** (`PriorityFlood`): fill sinks. Filled depressions deeper than a threshold become lakes. Worlds with no ocean keep endorheic lakes, which gives the desert its oases.
4. **Rivers** (`RiverCarver`): D8 flow directions with torus wrap, then flow accumulation. Patches with accumulation above a threshold become river (shallow water). Width scales with $\sqrt{\text{accumulation}}$.
5. **Moisture** (`MoistureModel`): the preset's base humidity + exponential decay with distance to water + orographic lift (windward slopes wetter, lee side in rain shadow along the prevailing wind).
6. **Base temperature** (`ThermalBase`): a periodic latitude profile and the lapse rate (§3.6).
7. **Biomes** (`BiomeClassifier`): a Whittaker-style lookup on (mean annual temperature, annual precipitation) → terrain id. Overrides: rock on steep or high ground, beach at the water margin, wetland on flat, wet lowland.
8. **Feature stamps** (`FeatureStamper`): oases, volcanic vents, cave systems (cellular automaton: 45% random fill, then 5 smoothing passes, connected to surface entrances), flood plains and scheduled rift lines.
9. **Vegetation initialization**: each food layer starts at $0.7K$ times log-normal noise; canopy starts at the terrain's canopy maximum.
10. **Founder placement** (`FounderPlacer`): each archetype has a habitat-suitability map (terrain preference × temperature fit × food availability × distance to water). Herds are sampled as clusters and solitary species are spread by Poisson-disk sampling.

---

## 3.6 Climate

### Temperature

$$
T(x,y,t) = \underbrace{T_{eq} - \tfrac{\Delta T_{lat}}{2}\left(1-\cos\tfrac{2\pi (y-y_{eq})}{H}\right)}_{\text{latitude (periodic, seamless)}}
\; - \; \underbrace{\Gamma\,\max(0,\,z-z_{sea})}_{\text{lapse rate}}
\; + \; \underbrace{A_s(y)\sin\!\left(\tfrac{2\pi(t-\phi_s)}{Y}\right)}_{\text{season}}
\; + \; \underbrace{A_d(x,y)\sin\!\left(\tfrac{2\pi(h-9)}{24}\right)}_{\text{diurnal, peak ≈ 15:00}}
\; + \; \underbrace{\omega_t}_{\text{weather}}
\; + \; \underbrace{\delta_{terrain}}_{\text{e.g. volcanic +8}}
\; + \; \underbrace{\Delta T_{drift}(t)}_{\text{climate change}}
$$

- $\Gamma = 6.5$ °C/km (the standard environmental lapse rate).
- The reference design's linear gradient $T_0 + \Delta T\,x/W$ would create a 30 °C cliff at the torus seam. The **periodic cosine profile** keeps the world seamless: the equator sits at $y_{eq}$ and the "poles" meet at the seam.
- Diurnal amplitude: $A_d = A_{d,0}\,(1 - \text{damping}_{terrain})\,(1 - 0.5\,\text{cloud})\,(1 - 0.6\,\text{water proximity})$.
- The weather anomaly follows an AR(1) process: $\omega_t = \rho\,\omega_{t-1} + \sigma\,\varepsilon_t$ with $\rho = 0.97$ and $\sigma$ set by the preset.
- Clouds cool the day and warm the night by $\pm c_{cloud}$.

### Weather (`WeatherMarkovChain`)

The weather states are `clear`, `cloudy`, `fog`, `rain`, `storm` and `snow`. Rain becomes snow when $T < 0$ °C. Each season has its own transition matrix, which is how presets express wet and dry seasons. The chain is advanced once per tick.

- **Rain cells:** precipitation is not uniform. Rain cells are thresholded noise blobs, advected with the wind, so storms visibly sweep across the map in replays.
- **Storms** double the wind, raise the hearing threshold (masking), cut vision by 40%, and ignite fires by lightning with probability $p_{lightning}\cdot\text{dryness}\cdot\text{fuel}$.
- **Wind:** a global vector that drifts by a random walk around the preset's prevailing direction, plus local noise.

### Climate drift (`ClimateDrift`)

Presets may define $\Delta T_{drift}(t)$, for example linear cooling of −6 °C over the run (Glacial Advance) or a step drought ($P \times 0.2$ for one season).

---

## 3.7 Light

$$
L(x,y,t) = \big[L_{sun}(h, \text{season}) + L_{moon}(t)\big]\,(1-0.6\,\text{cloud})\,(1-0.7\,\text{canopy})\,(1-\text{cave})
$$

- $L_{sun} = \max\!\big(0, \sin(\pi\,\frac{h - h_{rise}}{h_{set} - h_{rise}})\big)$, with day length $= 12 \pm A_{len}\sin(\text{season phase})$ hours, plus a smooth twilight ramp.
- $L_{moon} = 0.05\cdot\frac{1-\cos(2\pi t/T_{lunar})}{2}$.
- Light scales vision (see [04 §4.9](04-organism-model.md)), the growth of light-dependent food, and the renderer's color grading.

---

## 3.8 Hydrology

| Process | Model |
| --- | --- |
| Soil moisture (bucket) | $S_{t+1} = S_t + P/\theta_{cap} - k_{ET}\,f(T)\,S_t - k_{drain}\max(0, S_t - S_{fc})$, where $f(T)$ is a Q10-style evaporation factor |
| Surface water | $W_{t+1} = W_t + P + \text{inflow} - E(T,\text{wind},\text{humidity}) - \text{drinking}$. Lakes and rivers have a base level from generation; ponds appear where rain collects in depressions |
| Flood pulse (delta, wetland presets) | Floodplain water level $= W_0 + A_f\sin(2\pi t / Y + \phi_f)$; low patches become shallow or deep water in season |
| Snowpack | $\text{snow}_{t+1} = \text{snow}_t + P_{snow} - k_{melt}\max(0, T)$ (degree-tick melt model) |
| Drinkable | A patch or its neighbor has `surface_water ≥ 0.05 m` and is not frozen (T > −2 °C, or the animal can break thin ice) |

---

## 3.9 Primary producers (food layers)

Plants, fungi and invertebrates are **fields, not organisms**. Only animals are Jev-driven decision-makers. There are seven food layers:

| Layer | Grows in | Eaten by (diet axis) | Energy density (EU/kg dry) | Phenology |
| --- | --- | --- | --- | --- |
| `grass` | grassland, savanna, tundra (lichen), marsh | grazers (fiber) | 17,000 | Grows in warm, wet seasons; dormant in winter or dry season |
| `browse` (leaves, twigs) | forest, rainforest, savanna | browsers (fiber) | 16,000 | Deciduous presets drop to 20% in winter |
| `fruit` | forest, rainforest | frugivores (soft plant) | 20,000 | **Pulse**: fruiting windows by biome; ripe fruit rots |
| `seeds` | grassland, savanna, desert, rock | granivores (soft plant) | 22,000 | Set at the end of the growing season from grass biomass; long-lived seed bank |
| `invertebrates` | litter, soil, water margins | insectivores (animal) | 21,000 | Tracks moisture and detritus |
| `algae` | water | filter-feeders and waders (soft plant) | 14,000 | Light- and nutrient-limited |
| `fungi` | caves, forest floor, volcanic | fungivores (soft plant) | 15,000 | Grows on detritus; needs no light |

**Growth equation** for layer $f$ on a patch:

$$
F_{t+1} = F_t + r_f\, g_T\, g_W\, g_L\, g_N\; F_t\Big(1 - \frac{F_t}{K_f}\Big) + D_f\nabla^2 F_t + s_f - C_t - B_t
$$

- $g_T = \exp\!\big(-((T - T_{opt,f})/\sigma_f)^2\big)$ (thermal optimum)
- $g_W = \frac{S}{S + K_S}$ (Monod saturation in soil moisture)
- $g_L = \frac{\bar L_{day}}{\bar L_{day} + K_L}$ (light; equal to 1 for fungi and invertebrates)
- $g_N = \frac{N}{N + K_N}$ (soil nutrients)
- $D_f\nabla^2F$: seed dispersal and spread into neighboring patches (5-point Laplacian with torus wrap)
- $s_f$: a tiny seed-rain floor so overgrazed patches can recover, slowly
- $C_t$: consumption by animals; $B_t$: fire loss
- $K_f = K_{f,terrain}\cdot\text{productivity scale}\cdot\text{canopy factor}$ (browse and fruit scale with canopy)

Low biomass regrows slowly (the logistic term is proportional to $F$), so **overgrazing collapses a patch** until seed rain and neighbors restore it. This is a realistic source of herd movement.

**Fruit pulse:** $F_{fruit}$ gains $P(t) = \text{peak}\cdot\exp(-((t \bmod Y - t_{peak})/w)^2)$ per tick and loses $k_{rot}F$. Rotting fruit feeds soil nutrients and invertebrates.

**Canopy:** $C_{t+1} = C_t + r_c C_t (1 - C_t / C_{max})$ − browsing damage − fire. After a fire, canopy restarts at 0.05 and takes about 1.5 years to recover.

---

## 3.10 Detritus and nutrients (closing the loop)

$$
N_{t+1} = N_t + \underbrace{\eta_c\,\Delta m_{carcass}}_{\text{decay}} + \underbrace{\eta_x\,\text{excretion}}_{\text{unassimilated food}} + \underbrace{\eta_r\,\text{rotting fruit}}_{} + w_{base} - \underbrace{u\cdot\text{production}}_{\text{uptake}} - \ell N_t
$$

**Carcass decay:**

$$m_{t+1} = m_t\,\exp\!\big(-k_d\,Q_{10}^{(T-20)/10}\big), \qquad Q_{10} = 2.5$$

The decomposed mass feeds nutrients, invertebrates and the `carrion` scent source. Spoilage is $s = 1 - e^{-k_s\,\text{age}}$. Eating spoiled meat carries an infection risk unless the eater has a high `carrion_tolerance` gene (see [05 §5.5](05-ecology-rules.md)).

**Energy flows** sun → producers → herbivores → carnivores and scavengers → detritus → soil → producers. The loop is closed, which makes it the substrate of a realistic food web.

---

## 3.11 Chemical landscape (smell)

Each scent channel $C$ evolves by explicit diffusion–decay–advection:

$$
C_{t+1} = (1-\lambda_{cell})\Big[\,\mathcal{A}_{\vec w}\big(C_t + D\,\nabla^2 C_t\big)\Big] + S_t
$$

- $\nabla^2$ is the 5-point Laplacian computed with `np.roll` (the torus wrap is free). The explicit scheme is **stable only for $D \le 0.25$**, and the parameter validator enforces it.
- $\mathcal{A}_{\vec w}$ is a semi-Lagrangian shift along the wind vector with bilinear interpolation, so scents drift downwind. Prey that stay downwind of predators smell them first.
- $\lambda_{cell} = \ln 2 / t_{1/2}$, multiplied by 4 over deep water, 2 over shallow water and 2 during rain. **Crossing water breaks a scent trail.**

| Channel | Source $S_t$ | Half-life (ticks) | Who cares |
| --- | --- | --- | --- |
| `fruit_aroma` | ripe fruit mass | 3 | frugivores |
| `carrion` | carcass decay rate | 6 | scavengers, predators |
| `blood` | injuries and kills (pulse) | 2 | predators, prey (danger cue) |
| `water` | surface water (static-ish) | 12 | thirsty animals ("smell of water, faint, west") |
| `smoke` | fire intensity | 2 | everyone (flee) |
| `alarm_pheromone` | injured or distressed animals | 2 | conspecifics |
| `estrus` | females in estrus | 4 | mature males of the same species |
| `musk[species]` | every living animal, $\propto M^{0.75}(1-\text{scent masking})$ | 4 | predators (prey scent), prey (predator scent, i.e. kairomones) |

Musk channels are allocated dynamically, one per living species (at most 16). Territory marks are entities rather than a field, because they belong to individuals.

---

## 3.12 Sound (`SoundBoard`)

Sounds are events. Each event has a source, a kind (a call type, footsteps, a fight, a death cry, a splash) and a source level $L_0$ in dB.

$$
L_r = L_0 - 20\log_{10}\!\big(\max(d, 1)\big) - \alpha_{terrain}\,d - \beta_{rain}\,\text{rain}\cdot d
$$

- A sound is audible if $L_r > \theta_{hear}(\text{hearing acuity}) + \text{masking}(\text{wind}, \text{storm})$.
- Bearing is quantized to 8 directions with an error that shrinks with acuity.
- **Sounds are heard on the tick after they are made** (see [02 §2.4](02-architecture.md)).
- Movement at `hurried` or `all-out` effort makes footstep noise $\propto M^{0.5}$. Stealthy animals (`stalk`, `freeze`) make none.

---

## 3.13 Disturbances

| Disturbance | Trigger | Model | Ecological effect |
| --- | --- | --- | --- |
| **Wildfire** | Lightning in storms, eruptions, preset schedule | Cellular automaton: a burning patch ignites each neighbor with $p = p_0\cdot\text{fuel}\cdot\text{dryness}\cdot(1 + \cos\angle(\vec{w}, \text{dir}))\cdot(1 - S)$ and burns for 1–3 ticks | Removes grass, browse and canopy. Kills or injures animals caught in it. Smoke scent. **Post-fire flush**: +40% grass growth for a season from the nutrient pulse |
| **Flood pulse** | Seasonal (delta, wetland) | Floodplain level sinusoid (§3.8) | Drowning risk, nutrient deposition, algae boom |
| **Drought** | Stochastic or scheduled | Precipitation × 0.2, evaporation × 1.5 for a season | Waterholes shrink, herds concentrate, disease transmission rises |
| **Eruption** | Volcanic presets (Poisson with a low rate, or scheduled) | Lava zone (lethal) within radius $r_1$, ash zone $r_2$ (light × 0.5, grass × 0.2), toxin plume | Local extinction, then recolonization. Toxin-resistance selection |
| **Rift** | The Sundering preset, at tick $t_r$ | A sinuous line of patches goes to shallow water, then deep water over 100 ticks | Vicariance: two isolated populations |
| **Glaciation** | Glacial Advance preset | $\Delta T_{drift}$ ramps down; persistent snow above 80 cm becomes an ice surface (tundra-like, no food) | Range shifts, cold adaptation, possible extinction |
| **Epidemic** | Scheduled patient zero or a spill-over from a carcass | See [05 §5.13](05-ecology-rules.md) | Population crash, immune evolution |

---

## 3.14 Performance targets

- All field updates are vectorized numpy on `float32`. At 160×160, each update takes about 1–3 ms, and the whole environment phase set stays under 30 ms per tick.
- Perception uses the spatial hash plus Bresenham rays up to radius 12. With 300 organisms that is under 30 ms per tick.
- The field phases do not depend on decisions, so they could run concurrently with `DeliberationPhase`'s network wait. **They do not**, in order to keep the barrier semantics clean. The CPU is not the bottleneck; Jev throughput is.
