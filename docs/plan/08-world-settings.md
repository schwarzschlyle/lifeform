# 08 — World Settings

There are twelve core worlds and two stretch worlds. Each is a scientific scenario with a question it is built to answer, and each has its own visual identity. A world is a YAML preset (`presets/<slug>.yaml`) consumed by `WorldBuilder`. No world needs special-case code: every difference is parameters, feature stamps and scheduled disturbances.

---

## 8.1 Overview

| # | World | Biome | Grid | Founders | Signature mechanic | Core question | Standard ticks |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | **Serengeti Pulse** | Savanna | 192² | 80 | Moving rain belt, waterholes, fire | Does migration emerge from a moving food pulse? | 1,500 |
| 2 | **Galápagos Scatter** | Archipelago | 160² | 75 | Isolated islands, rafting | Adaptive radiation and island size shifts? | 1,500 |
| 3 | **Boreal Long Night** | Taiga / tundra | 160² | 78 | Deep snow, long winter nights | Bergmann's rule, fat and insulation, winter strategies? | 1,500 |
| 4 | **Oasis of Salt** | Desert | 160² | 89 | Scarce water, 40 °C day–night swing | Nocturnality and water economy? | 1,500 |
| 5 | **Emerald Canopy** | Rainforest | 160² | 80 | Patchy fruit, low light, climbing | Aposematism and niche partitioning? | 1,500 |
| 6 | **Delta of Tides** | Wetland delta | 192² | 80 | Seasonal flood pulse | Amphibious traits and flood-timed breeding? | 1,500 |
| 7 | **Ashfall Caldera** | Volcanic highland | 160² | 76 | Eruptions, toxic vents, geothermal refuges | r-selection and toxin resistance under disturbance? | 1,500 |
| 8 | **Spine of the World** | Mountains | 192² | 75 | Altitudinal zonation, passes | Clines and altitudinal migration? | 1,500 |
| 9 | **Twilight Ring** | Tidally locked planet | 192² | 70 | No day–night cycle; habitable terminator | How do circadian and vision traits evolve without day and night? | 1,500 |
| 10 | **Red Queen Pit** | Minimal arena | 96² | 70 | Two species, high mutation | Lotka–Volterra cycles and a coevolutionary arms race? | 3,000 |
| 11 | **Pale Plague Meadow** | Grassland | 160² | 102 | Evolving pathogen, waterhole transmission | SEIR dynamics, and virulence and immune evolution? | 1,500 |
| 12 | **The Sundering** | Temperate continent | 192² | 85 | A rift splits the world at tick 500 | Allopatric speciation: drift versus selection? | 2,000 |
| S1 | Glacial Advance | Temperate to ice age | 192² | 80 | −8 °C climate drift | Adapt, move or die? | 2,000 |
| S2 | Lightless Hollows | Cave network | 128² | 60 | Zero light underground | Regressive evolution of eyes? | 2,000 |

**Standard-profile budget** for the 12 core worlds: 20,000 world-ticks (10 × 1,500 + 3,000 + 2,000) × about 80 mean organisms ≈ 1.6M calls ≈ 22 h at 1,200 RPM ≈ $87. The `preview` profile (300 ticks each) costs about $10 and takes about 2.5 h ([01 §1.8](01-jev-research.md)).

---

## 8.2 The worlds

### 1 · Serengeti Pulse

- **Concept:** a savanna whose rains move. A precipitation belt sweeps east and west across the map once a year, so the grass wave moves and grazers must follow it or starve.
- **Map:** gentle rolling plains, one river, 6–8 waterholes (lakes that shrink in the dry season), acacia savanna patches, kopjes (rock outcrops) giving cover, and a thicket belt in the north.
- **Climate:** tropical, 22–34 °C. The four seasons are named *early wet*, *late wet*, *early dry* and *late dry*. The rain-belt center is $x_c(t) = W/2 + A\sin(2\pi t/Y)$ with a Gaussian band width of $W/5$.
- **Disturbances:** lightning fires in the late dry season and a post-fire grass flush.
- **Founders:** Meadow Grazer ×50 (3 herds), Thicket Browser ×12, Pack Runner ×8 (2 packs), Stripe Stalker ×4, Carrion Strider ×6.
- **Watch for:** herd migration tracking green-up; the selfish-herd geometry under predation; scavenger–predator following; fire-scar grazing; kin-biased alarm calling.
- **Experiment variant:** `serengeti-pulse-no-predators` tests for a **trophic cascade** by comparing vegetation biomass.
- **Look:** golden grass, ochre earth, flat-topped acacia greens, heat shimmer at midday, and apricot-to-violet dusk grading.

### 2 · Galápagos Scatter

- **Concept:** seven islands with different food menus, colonized from one source island. The classic adaptive-radiation setup.
- **Map:** 70% ocean. Islands range from a large mixed-forest island down to tiny rocks. Arid seed islands, fruit-forest islands, invertebrate-rich beaches and algae reefs.
- **Climate:** mild tropical with low seasonality. A scheduled "El Niño" drought year at tick 700 (precipitation × 0.25 for one season).
- **Special rules:** deep water separates islands, and swimming requires swim skill > 0.5 plus stamina. **Rafting** is a world event (probability 0.002 per tick) that carries 1–3 animals from a coast to another island. It is *sweepstakes dispersal*: the animals do not choose it. There are no large predators (predator release), and $\delta_{iso} = 0.18$.
- **Founders:** Bristle Forager ×40, Burrow Hopper ×20 and Reed Wader ×15, all on the largest island.
- **Watch for:** diet-simplex divergence between islands; body-size shifts (dwarfism or gigantism); speciation events; post-drought bottlenecks.
- **Look:** turquoise shallows, black basalt, cactus greens and white-sand halos, with wave foam animated at the coasts.

### 3 · Boreal Long Night

- **Concept:** a world ruled by winter: deep snow, short days, and stored fat as the currency of survival.
- **Map:** taiga forest mosaic, frozen lakes, tundra in the cold band and bogs.
- **Climate:** mean 0 °C, seasonal amplitude ±18 °C, day length 12 ± 8 h. Snowpack reaches 100 cm and buries grass; browse drops to 20% in winter.
- **Founders:** Thicket Browser ×30 (moose-like), Burrow Hopper ×30 (hare-like), Pack Runner ×8, Grub Snuffler ×10.
- **Watch for:** **Bergmann's rule** (mass increases), the rise of insulation and fat capacity, huddling and den use, winter mortality spikes, and breeding-season timing.
- **Look:** blue-white snow, dark spruce teal, and **aurora ribbons** in the night sky layer.

### 4 · Oasis of Salt

- **Concept:** water is the limiting resource. Life clusters around oases, and daytime heat kills.
- **Map:** dunes, salt flats, rocky hamada, 4 oases (lakes with palm-like forest rings), and a **wadi** that runs with water only after the rare storms.
- **Climate:** 45 °C by day and 5 °C by night. Rain comes only from rare storm states; the wadi flows for about 12 ticks after a storm.
- **Founders:** Burrow Hopper ×35, Bristle Forager ×20, Grub Snuffler ×15, Shell Crawler ×15, Stripe Stalker ×4.
- **Watch for:** a shift in `activity_phase` toward nocturnality, rising water efficiency, more burrowing, whether ectothermy wins, overgrazing collapse around oases, and oasis disease hot spots.
- **Look:** dune apricot, salt-white glare, emerald oases, and a deep indigo night with a star field.

### 5 · Emerald Canopy

- **Concept:** abundant but patchy food under a dark canopy, where many niches coexist.
- **Map:** 85% rainforest, rivers and oxbow lakes, a few clearings, and fruiting trees that fruit **asynchronously** (a staggered phenology per patch cluster).
- **Climate:** 24–30 °C, high humidity, rain most days.
- **Founders:** Bristle Forager ×25, Shell Crawler ×20 (with founder alleles for toxicity and ornament deliberately variable), Grub Snuffler ×20, Reed Wader ×10, Stripe Stalker ×5.
- **Watch for:** **aposematism**, meaning the co-evolution of toxicity and ornament as predators learn; niche partitioning by diet and height (climbing); and olfaction or hearing gaining weight over vision in low light.
- **Look:** deep emerald layers, drifting mist, orchid-magenta highlights, and sunbeams through clearings.

### 6 · Delta of Tides

- **Concept:** a landscape that floods and drains every year.
- **Map:** a branching river delta, reed beds, mudflats, levee ridges, and islands that appear and vanish.
- **Climate:** subtropical. A **flood pulse** with amplitude 1.2 m peaks in late summer; floodplain patches cycle between land and water.
- **Founders:** Reed Wader ×35, Meadow Grazer ×25 (buffalo-like override: swim 0.5), Shell Crawler ×15, and Stripe Stalker ×5 with a crocodile-like override (swim 0.8, endothermy 0.3, ambush).
- **Watch for:** swim-skill evolution, flood-timed breeding, drowning selection, ambush at drinking points, and pathogen persistence in mud.
- **Look:** silt browns, reed greens, silver water with a slow flow animation, and pale heron greys.

### 7 · Ashfall Caldera

- **Concept:** a cold highland with warm, toxic volcanic valleys and periodic destruction.
- **Map:** a central caldera lake, fumarole fields (toxic and warm), lava plains, and pine slopes.
- **Climate:** cool (mean 6 °C). Geothermal zones add +8 °C, creating winter refuges that are also toxic.
- **Disturbances:** minor eruptions as a Poisson process (mean interval 400 ticks) and a **major eruption at tick 600** (lava radius 12, ash radius 40).
- **Founders:** Burrow Hopper ×30, Bristle Forager ×20, Carrion Strider ×10, Shell Crawler ×10, Pack Runner ×6.
- **Watch for:** rising toxin resistance, a shift toward r-selection (larger litters), recolonization waves after eruptions, and winter use of the warm but toxic refuges.
- **Look:** basalt black, ember orange, sulfur yellow and drifting ash particles, with glowing lava as an emissive layer.

### 8 · Spine of the World

- **Concept:** a mountain range that folds a whole climate gradient into a short distance.
- **Map:** a central ridge that wraps across the torus and is crossable at 3 passes. Grassland foothills, montane forest, alpine meadow, scree and permanent snow.
- **Climate:** the lapse rate (6.5 °C/km) gives about 20 °C difference from valley to peak; the snowline moves with the seasons.
- **Founders:** Meadow Grazer ×30 (foothills), Thicket Browser ×15 (forest), Burrow Hopper ×20 (alpine), Pack Runner ×6, Stripe Stalker ×4.
- **Watch for:** **clines** in mass, insulation and fat with elevation; seasonal altitudinal migration; and gene flow through the passes versus divergence between valleys.
- **Look:** dramatic hillshade from a moving sun, slate and glacier blue, alpine greens, and golden light on the peaks at dawn.

### 9 · Twilight Ring

- **Concept:** an exoplanet locked with one face to its star. There is permanent day on one side and permanent night on the other, and life lives on the ring between them.
- **Map:** the substellar point is at the map center, and the angle from it is mapped radially using toroidal distance: the day side is a scorched desert, the terminator ring is lush, and the night side is ice. There are lakes along the ring and geothermal fungus fields on the night side.
- **Climate:** $T = T_{night} + (T_{day} - T_{night})\max(0, \cos\theta)^{1/4}$, with $T_{day} = 60$ °C and $T_{night} = -50$ °C. There is **no day–night cycle**: light is constant per location. A steady wind blows from the day side to the night side, which is ideal for testing scent drift.
- **Special rules:** the 12-tick "day" remains only as an internal clock. `activity_phase` has no environmental rhythm to follow.
- **Founders:** Bristle Forager ×30, Grub Snuffler ×20, Shell Crawler ×15, Stripe Stalker ×5.
- **Watch for:** relaxation of circadian traits, night-vision gains under dim red light, and thermal specialists spreading toward the hot and cold edges of the ring.
- **Look:** a crimson sun glow, violet shadows, an amber terminator and an ice-blue night side. It is the most otherworldly of the worlds.

### 10 · Red Queen Pit

- **Concept:** a minimal, clean coevolution experiment in the tradition of classic predator–prey studies.
- **Map:** a 96×96 uniform grassland with scattered cover and 2 ponds. Constant climate, no seasons, no disease.
- **Special rules:** mutation modifier ×2 at founding, two species only, and a longer run (3,000 ticks, about 210k calls, about 3 h, about $12).
- **Founders:** prey (a Burrow Hopper variant, grazer diet) ×60 and Pack Runner ×10.
- **Watch for:** **Lotka–Volterra oscillations** (the phase portrait), and arms-race trajectories in prey speed, vigilance and crypsis against predator speed, olfaction and stamina.
- **Look:** a minimalist, scientific aesthetic: pale sage field, crisp two-color creatures, and a live phase-portrait inset.

### 11 · Pale Plague Meadow

- **Concept:** a crowded grassland meets a new pathogen.
- **Map:** grassland with 5 waterholes, where the environmental pathogen accumulates.
- **Special rules:** patient zero is infected at tick 300 with a moderately virulent, water-shedding strain; strain mutation is on.
- **Founders:** Meadow Grazer ×70, Bristle Forager ×20, Pack Runner ×6, Carrion Strider ×6.
- **Watch for:** the SEIR epidemic curve, herd immunity, **behavioral avoidance** of animals that look sick, the evolution of immune investment and virulence, and whether predators remove the sick (the healthy-herds hypothesis).
- **Look:** pale green meadow, bone-white dusk, and a subtle chartreuse glow on infectious animals in the disease layer.

### 12 · The Sundering

- **Concept:** one population, then an impassable barrier, then divergence.
- **Map:** a temperate forest–grassland mosaic.
- **Special rules:** on a torus, **one** closed barrier does not split the surface into two regions. The rift is therefore **two parallel, wrapping water channels**, which leaves two disconnected bands. They open over ticks 500–600. After that, band A drifts warmer (+3 °C) and band B drier (precipitation × 0.7), which drives divergent selection. $\delta_{iso} = 0.18$.
- **Founders:** Meadow Grazer ×40, Bristle Forager ×20, Burrow Hopper ×20, Stripe Stalker ×5.
- **Watch for:** the time to the first speciation event, and divergence at neutral markers (drift) versus trait loci (selection), which is a direct drift-versus-selection readout.
- **Look:** calm temperate greens, then a dramatic cinematic moment as the blue rift tears open.

### S1 · Glacial Advance (stretch)

- A temperate world whose climate drift is −8 °C over 2,000 ticks. Persistent snow becomes ice sheets that spread from the cold band.
- **Watch for:** range shifts versus in-place adaptation versus extinction, and whether refugia form.

### S2 · Lightless Hollows (stretch)

- A 128² cave network (cellular-automaton caves) with surface entrance zones. Inside, light is zero and food is fungi and invertebrates.
- **Founders:** Grub Snuffler ×30, Bristle Forager ×20, Shell Crawler ×10.
- **Watch for:** **regressive evolution**: visual acuity falls because eyes cost BMR and give no benefit, while olfaction and hearing rise.
- **Look:** darkness lit by bioluminescent teal fungi and soft vision cones.

---

## 8.3 Preset file shape (configuration, not code)

```yaml
slug: serengeti-pulse
title: Serengeti Pulse
grid: { width: 192, height: 192 }
calendar: { ticks_per_day: 12, days_per_season: 12, season_names: [early wet, late wet, early dry, late dry] }
terrain:
  generator: savanna
  water_fraction: 0.06
  river_accumulation_threshold: 900
  feature_stamps:
    - { kind: waterholes, count: 7, radius_patches: [2, 5] }
    - { kind: kopjes, count: 12 }
climate:
  equator_temperature_c: 30
  latitudinal_range_c: 8
  diurnal_amplitude_c: 7
  rain_belt: { amplitude_fraction_of_width: 0.35, band_width_fraction: 0.2 }
  weather_transitions: presets/weather/tropical-wet-dry.yaml
disturbances:
  wildfire: { lightning_probability: 0.002, post_fire_flush_multiplier: 1.4 }
productivity_scale: calibrated
founders:
  - { archetype: meadow-grazer, count: 50, groups: 3 }
  - { archetype: thicket-browser, count: 12 }
  - { archetype: pack-runner, count: 8, groups: 2 }
  - { archetype: stripe-stalker, count: 4 }
  - { archetype: carrion-strider, count: 6 }
targets: { herbivores: 90, predators: 12, max_population: 300 }
palette: palettes/serengeti.json
```
