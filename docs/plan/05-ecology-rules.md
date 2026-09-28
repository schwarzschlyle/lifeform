# 05 — Ecology Rules: How Organisms Live, Eat, Kill, Reproduce and Die

Everything in this document is **code**: deterministic models driven by seeded randomness. Jev decides *what an animal tries to do*. These rules decide *what happens when it tries*.

---

## 5.1 Units and calibration philosophy

| Quantity | Unit |
| --- | --- |
| Mass | kg |
| Energy | EU (energy unit, nominally 1 kJ) |
| Temperature | °C |
| Time | tick (2 simulated hours; see [03 §3.2](03-world-model.md)) |
| Health, hydration, fear, sleep pressure | fraction 0–1 |

**Exponents are taken from the empirical literature** (Kleiber ¾, cost of transport −0.32, lifespan ¼, water turnover 0.8, and so on). **Coefficients are calibrated** so that populations settle in the band Jev throughput can afford (about 60–150 animals per world). This is the honest compromise. Relative rates (predator versus prey metabolism, digestion of meat versus grass, growth versus lifespan) are biologically grounded. Absolute primary productivity per patch is scaled by one number per world, $\psi$ (§5.16).

Default coefficients live in `EcologyParameters` / `PhysiologyParameters`. The values quoted here are starting points for calibration.

---

## 5.2 Energy budget (`MetabolicModel`)

$$
E_{t+1} = E_t + \underbrace{\sum_f \rho_f S_f\,\mathrm{ED}_f\,e_f}_{\text{digested}}
- \underbrace{B}_{\text{basal}}
- \underbrace{B\,(\mathrm{PAL}_{verb,effort}-1)}_{\text{activity}}
- \underbrace{L_{move}}_{\text{locomotion}}
- \underbrace{Q_{thermo}}_{\text{thermoregulation}}
- \underbrace{R_{repro}}_{\text{pregnancy, lactation, courtship}}
- \underbrace{I_{immune}}_{\text{active infection}}
- \underbrace{H_{cost}}_{\text{healing}}
$$

- $B$ is from [04 §4.5](04-organism-model.md), with $b_0 = 24$ EU·kg$^{-0.75}$ per tick (about 290 kJ·kg$^{-0.75}$ per day, the mammalian Kleiber constant).
- **PAL** (physical activity level) comes from the verb catalog ([06 §6.3](06-action-catalog.md)): rest 1.1, sleep 0.9, graze 1.5, fight 4.0, and so on. It is multiplied by the effort factor.
- $L_{move} = c_{loc}\,m^{0.68}\sum_{\text{steps}}\text{terrain cost}\cdot\sqrt2^{[\text{diagonal}]}\cdot\eta_{effort}$, with $\eta = (1.0, 1.0, 1.25, 1.7)$ for minimal, steady, hurried and all-out.
- **Catabolism:** when $E$ reaches 0, the deficit is drawn from lean tissue at $\rho_{lean} = 7{,}000$ EU/kg, so mass falls. Health takes starvation damage $\delta_s\cdot\text{deficit}/B$. When mass drops below $0.6 \times$ the structural (lean) mass, the animal dies of **starvation**.

**Worked example:** a 40 kg Meadow Grazer has $B \approx 24 \cdot 40^{0.75} \approx 380$ EU per tick. Its field metabolic rate is about 2.5 B, or 950 EU per tick. With 10% body fat, the reserve is 156,000 EU, about 160 ticks (13 days) of fasting. That is plausible for a mid-sized mammal.

---

## 5.3 Thermoregulation (`ThermalBlend` of endotherm and ectotherm strategies)

### Endotherm (Scholander–Irving)

- Heat balance at rest: $B = C\,(T_{b,set} - T_a)$ gives the **lower critical temperature** $T_{lc} = T_{b,set} - B/C$.
- Below $T_{lc}$: extra heat must be produced, $Q_{thermo} = C\,(T_{lc} - T_a)$. Large, insulated animals have low $C$ per unit of heat, which is why **Bergmann's rule** can emerge.
- The upper critical temperature is $T_{uc} = T_{lc} + \Delta_{TNZ}$, where the thermoneutral width grows with insulation and size.
- Above $T_{uc}$: evaporative cooling costs water, $W_{evap} = \kappa_e\,C\,(T_a - T_{uc})$. If hydration is below 0.2, cooling fails, $T_b$ rises, and the animal takes **overheating** damage.
- When reserves are exhausted in the cold, $T_b$ falls and the animal takes **hypothermia** damage.

### Ectotherm

- Body temperature relaxes toward the **operative temperature**: $T_b' = T_b + k_h\,(T_{op} - T_b)$, with $k_h = k_0\,m^{-0.33}$ (big bodies have thermal inertia).
- $T_{op} = T_a + \text{solar gain}\cdot L\cdot[\text{basking}] - \text{shade cooling}\cdot[\text{shade}] - \text{water cooling}\cdot[\text{in water}]$.
- **Thermal performance curve** (asymmetric, as in real ectotherms):

$$
P(T_b) = \begin{cases} \exp\!\big(-((T_b - T_{opt})/2\sigma)^2\big) & T_b \le T_{opt} \\ \max\!\big(0,\ 1 - ((T_b - T_{opt})/(CT_{max}-T_{opt}))^2\big) & T_b > T_{opt} \end{cases}
$$

  $P$ multiplies speed, attack power and digestion rate. Metabolism scales as $\Theta = Q_{10}^{(T_b - T_{ref})/10}$ with $Q_{10} = 2.5$.
- Outside $[CT_{min}, CT_{max}]$ the animal takes damage (hypothermia or hyperthermia).

### Blend

The `endothermy` gene $\epsilon$ mixes the two models. $T_b = \epsilon\,T_{b,set} + (1-\epsilon)\,T_{b,ecto}$, thermoregulatory costs scale by $\epsilon$, and basal cost scales by $0.15 + 0.85\epsilon$. That is a smooth axis along which evolution can move.

**Behavioral thermoregulation is Jev's job:** `bask`, `seek_shade`, `huddle`, `wallow`, `enter_den`. A den buffers temperature: $T_{den} = 0.3\,T_a + 0.7\,\bar T_{annual}$. The state tells the animal how it feels ("cold") and what is available ("a sunny rock", "shade to the west").

---

## 5.4 Water balance (`WaterBalanceModel`)

$$
h_{t+1} = h_t - \frac{w\,(1-0.6\,\text{water eff.}) + W_{evap} + W_{lactation}}{V_{body}} + \frac{\text{drunk} + \text{food water}}{V_{body}}, \qquad V_{body} = 0.6\,m
$$

- **Food water content:** fruit 80%, invertebrates 70%, meat 65%, green grass 60% (wet season) or 15% (dry season), seeds 10%, algae 90%.
- **`drink`** delivers up to $\min(\text{deficit},\ d_0\,m^{0.8}\cdot\eta_{effort})$ per tick from a drinkable patch.
- Effects of dehydration: below $h = 0.3$, performance is multiplied by $0.5 + h/0.6$. Below 0.1, health takes damage. At $h = 0$ for 2 ticks, the animal dies of **dehydration**.

---

## 5.5 Feeding and digestion (`DigestionModel`, `BiteModel`, `ResourceSharing`)

### Intake per eating action

$$
I_f = \min\!\big(i_{max}\,k_f\,\eta_{effort}\,P(T_b)\cdot\text{skill}_f,\ \ A_f\cdot\text{access},\ \ S_{max} - S\big)
$$

| Food | Handling factor $k_f$ | Skill modifier | Digestion rate $\rho_f$ per tick | $e_{max}$ (specialist assimilation) |
| --- | --- | --- | --- | --- |
| grass | 1.0 | grazer–browser gene near 0 | 0.15 | 0.55 |
| browse | 0.7 | grazer–browser gene near 1; climbers get +20% | 0.15 | 0.50 |
| fruit | 1.2 | climb skill +30% in rainforest | 0.35 | 0.80 |
| seeds | 0.4 | dig skill | 0.30 | 0.75 |
| invertebrates | 0.3 | dig skill ×(0.5 + dig) | 0.40 | 0.80 |
| algae | 0.6 | swim skill | 0.35 | 0.60 |
| fungi | 0.8 | — | 0.30 | 0.60 |
| meat (fresh carcass) | 1.5 | weaponry (to open it) | 0.40 | 0.85 |
| carrion (spoiled) | 1.5 | — | 0.40 | 0.85 × (1 − 0.4 · spoilage) |

- **Assimilation:** $e_f = e_{max,f}\sqrt{d_k}$, where $d_k$ is the organism's diet-simplex weight for the food's class (fiber, soft plant or animal).
- **Excretion:** the unassimilated fraction $(1 - e_f)$ returns to soil nutrients at the organism's position, which closes the loop.
- **Holling type II** functional response *emerges*: search time is the ticks spent moving to food, and handling time is set by the bite rate and stomach capacity.
- **Contested patch:** when several organisms eat the same patch or carcass in a tick, intake is split in proportion to $10^{R/400}\cdot m^{0.75}$, where $R$ is the Elo dominance rating.
- **Spoiled meat:** eating carrion with spoilage $s$ carries an infection risk $p = 0.3\,s\,(1 - \text{carrion tolerance})$, as food poisoning (toxin load) or a pathogen strain.
- **Toxic prey:** eating tissue of a toxic organism adds toxin load $\propto \text{toxicity}\cdot\text{bite}/m$ and triggers a Rescorla–Wagner update with $\lambda = -1$ for that species. **Predators learn aposematism.**
- **Trampling:** animals above 100 kg reduce grass on the patches they cross by 1% per pass.

---

## 5.6 Growth and life stages

| Stage | Entry | Characteristics |
| --- | --- | --- |
| **Newborn** | birth | Dependent. Altricial young cannot move for $0.5\,A_{wean}(1-\text{precociality})$ ticks. They are fed by nursing and have a reduced affordance menu |
| **Juvenile** | weaning ($A_{wean}$) | Forages alone and grows by the West model ([04 §4.5](04-organism-model.md)). Inherits the mother's top 3 spatial memories |
| **Adult** | $A_{mat}$ and $m \ge 0.7\,M_\infty$ | Can reproduce |
| **Senescent** | $a > 0.6\,\mathcal L$ | Performance multiplier $1 - 0.5\big((a - 0.6\mathcal L)/\mathcal L\big)$, lower fertility, slower healing |

---

## 5.7 Health, injury and healing (`HealingModel`)

- **Damage sources** are recorded in a per-organism `DamageLedger` so a death can be attributed: bites and strikes, falls, fire, lava, toxin, starvation, dehydration, heat, cold, disease and parasites.
- **Wounds:** each strike creates a wound with severity $\propto$ damage. A bleeding wound drains 0.02 health per tick and stops with probability 0.3 per tick (0.6 when resting). A wound with severity above 0.3 on a limb causes `limping` (speed × 0.6).
- **Healing:** $\Delta H = h_{heal}\,m^{-0.25}\cdot(2\ \text{if resting or asleep})\cdot\mathbb 1[E/E_{max} > 0.2]\cdot(1 - 0.5\,\text{stress})\cdot\text{healing rate}$. It costs $c_h$ EU per unit healed.
- **Pain** rises with damage and decays with a half-life of 3 ticks. It appears in the state and increases fear through the threat appraisal.

---

## 5.8 Sleep, fatigue and stamina

**Two-process sleep model (Borbély):**

- While awake: $S_{t+1} = 1 - (1 - S_t)\,e^{-1/\tau_w}$ with $\tau_w = 14$ ticks.
- While asleep: $S_{t+1} = S_t\,e^{-1/\tau_s}$ with $\tau_s = 3$ ticks.
- Circadian drive: $C(t) = \cos\!\big(2\pi(h - h_{peak}(\text{activity phase}))/24\big)$. Diurnal animals peak at midday and nocturnal ones at midnight.
- Sleepiness $= S - 0.3\,C$ is shown as words.

**Sleep deprivation** ($S > 0.85$): perception certainty × 0.7, initiative −1 rank, and the words "exhausted".

**Sleeping exposed** is dangerous. A sleeping animal is described to others as "asleep", and attacks on it get the surprise bonus. Sleeping in a den or hidden patch reduces detection by 70–90%.

**Stamina** (short-term): hurried effort costs 0.15 per tick and all-out costs $1/\text{stamina ticks}$. Stamina recovers 0.2 per tick at minimal or steady effort and 0.35 per tick at rest. At 0 the animal is `exhausted` and its effort is capped at steady.

---

## 5.9 Predation and combat (`AttackModel`, `PursuitModel`, `GroupDefense`)

### Sequence within a tick

1. **Movement sub-steps** ([06 §6.7](06-action-catalog.md)): the attacker's `attack`, `chase` or `stalk` intent moves it toward the target, and the prey's `flee` moves it away. Each step is interleaved by initiative, so speed differences decide chases.
2. **Reachability:** a target that is `climbing` (attacker climb < 0.5), `in_den` (attacker dig < 0.6), in deep water (attacker swim < 0.5) or otherwise out of reach cannot be struck.
3. **Strike** if the attacker ends adjacent to the target.

### Strike success

$$
P_{hit} = \sigma\Big(\beta_0 + \beta_1\ln\frac{A_{att}}{D_{def}} + \beta_2\,\text{surprise} + \beta_3\,\text{stalked} + \beta_{pack}\,n_{co} - \beta_4\ln(1 + n_{group}) - \beta_5\,\text{cover} + \beta_6(\text{fatigue}_{def} - \text{fatigue}_{att}) - \beta_7\,\text{brace}\Big)
$$

| Term | Meaning | Default β |
| --- | --- | --- |
| $\ln(A/D)$ | power ratio (includes mass through $m^{0.66}$) | 1.2 |
| surprise | the target did not perceive the attacker at the start of the tick, or is asleep | 1.5 |
| stalked | the attacker used `stalk` or `ambush` last tick without being detected | 0.8 |
| $n_{co}$ | other pack members striking the same target this tick | 0.6 each |
| $\ln(1 + n_{group})$ | **confusion effect**: conspecifics of the target within 2 patches | 0.5 |
| cover | cover value of the target's patch | 0.8 |
| fatigue difference | stamina deficit of each side | 1.0 |
| brace | the target chose `brace` or `defend_young` | 0.9 |

### Outcome

- **Damage:** $\text{dmg} = A_{att}\,U(0.7, 1.3)\,(1 - 0.7\,\text{armor}_{def})$, converted to health fraction by $H_{abs,def}$. It adds a bleeding wound, a pain spike, a `blood` scent pulse and a fight sound event.
- **Kill:** $H \le 0$ causes death by **predation** (heterospecific attacker) or **combat** (conspecific). A **carcass** is created with $0.6\,m$ kg of meat.
- **Active retaliation:** if the target chose `fight_back`, `brace`, `attack` or `defend_young` and is adjacent, it counter-strikes with the same formula and no surprise.
- **Passive retaliation:** horns and spines hurt attackers anyway, doing $0.3\,A_{def}\,\text{weaponry}_{def}$ when the attacker's strike lands.
- **Toxic prey:** biting a toxic target adds toxin load to the attacker even when the strike does not kill.

### Pursuit

A prey animal that ends its movement more than 1 patch away escapes the strike this tick. Stamina limits how many consecutive all-out ticks either side can sustain. Refuges break a pursuit: cover, water, trees and dens where the pursuer lacks the skill to follow.

### Group behaviors

| Behavior | Mechanism |
| --- | --- |
| **Dilution** | A predator chooses one target through its affordance, so each herd member faces lower individual risk |
| **Many eyes** | A `sentinel` or `scan_surroundings` choice gives +30% detection radius. An alarm call is heard by all within range next tick |
| **Confusion** | the $\ln(1 + n_{group})$ term above |
| **Cooperative hunting** | the $\beta_{pack}$ term above. Larger prey become profitable for packs |
| **Mobbing** | Several animals choosing `mob_X` while adjacent to predator X each deal small damage and give X a `harassed` condition. Whether it retreats is Jev's decision |
| **Playing dead** | A `play_dead` animal is described to others as "lying limp, seems dead". Jev decides whether predators lose interest |

---

## 5.10 Reproduction (`CourtshipModel`, `ConceptionModel`, `Pregnancy`, `Litter`)

### Eligibility

| Sex | Conditions |
| --- | --- |
| Female | adult; not pregnant; not lactating with unweaned young (lactational anestrus); $E/E_{max} \ge 0.4$; $H \ge 0.5$; in the breeding season, with strictness set by the `breeding_seasonality` gene. **Estrus**: 12 ticks in each 48-tick cycle while eligible, during which she emits `estrus` scent |
| Male | adult; $E/E_{max} \ge 0.3$; $H \ge 0.4$ |

### Courtship and consent (both animals choose, through Jev)

1. **`court_X`** is chosen by an eligible animal within 2 patches of an eligible partner. It costs PAL 2.0, raises detectability (display), and sets the condition `courted_by:<courter>` on X for the next tick.
2. X's next state includes *"P7 is courting you: {display words}"*. The display words come from ornament × health × energy × dominance: "a dull, half-hearted display" through "a vivid, vigorous, impressive display".
3. X's affordances then include **`mate_with_P7`**, which is legal if P7 is adjacent after movement and courted within the last 2 ticks. Not choosing it is rejection. Mate choice is therefore Jev's judgment, informed by the chooser's `mate_choosiness` words, so **sexual selection emerges**.
4. Mating takes the tick for both animals, and both are vulnerable while mating.

### Conception

$$
p_c = f_{age}(a)\cdot H\cdot\sqrt{E/E_{max}}\cdot F_{compat},\qquad F_{compat} = \max\!\big(0,\ 1 - (\delta/\delta_{iso})^2\big)
$$

$f_{age}$ is a fertility curve that peaks in mid-adulthood and declines in senescence. $\delta$ is the genetic distance (§5.11). If the female mates several times within one estrus, the first successful conception sets paternity.

### Pregnancy

- Duration $G$ ([04 §4.5](04-organism-model.md)).
- Extra energy cost per tick: $R_{repro} = 1.5\,\rho_{lean}\,M_{litter}/G$.
- Mass increases, and mobility is × 0.9 in the last third of pregnancy.
- **Resource-dependent loss:** if $E < 0.15\,E_{max}$, there is a 5% chance per tick of miscarriage (an event, not a death).

### Birth (a physiological event, not an action)

- The litter size $n$ comes from `offspring_investment`, and the total litter mass is $\varphi M_\infty$ with $\varphi = 0.08\,(1 + 0.5\,\text{precociality})$.
- Newborns are placed on or adjacent to the mother. If she is in a den she built (`nest_building`), the young start hidden and warm and get a survival bonus.
- Maternal death at birth has probability $0.005\cdot(M_{litter}/(0.1\,m))$, recorded as the cause **birth complications**.
- **Each newborn is a full organism and gets its own Jev call from its first tick.** Its menu is small: rest, call, suckle, crawl toward mother, hide.

### Parental care

| Mechanism | Rule |
| --- | --- |
| Nursing | A mother choosing `nurse_X` (X adjacent) transfers $\min(\text{need},\ \nu\,m^{0.75})\times0.8$ EU; she pays 1.25×. A young choosing `suckle` receives half that without the mother's choice, or the full amount if both chose |
| Guarding | `defend_young` keeps the parent adjacent. Attacks on the young face the parent's retaliation first, and the young get a cover bonus |
| Provisioning | `carry_food` + `share_food_with_X` lets fathers and helpers feed young. **Biparental care can evolve** |
| Weaning | At $A_{wean}$ lactation stops, the young become independent, and they inherit the mother's top memories |
| Orphans | Unweaned young whose mother died can still forage if they are precocial. Otherwise they starve, recorded as starvation (orphaned) |

Nothing forbids infanticide or kleptoparasitism. If they emerge, they emerge from Jev's choices and the rules above.

---

## 5.11 Genetics (`Recombination`, `Mutation`, `GeneticDistance`)

- **Genome:** 89 loci, diploid: 57 trait loci, 24 instinct loci, and **8 neutral marker loci** that affect nothing and serve as a molecular clock for drift and phylogeny.
- **Gamete formation:** within each linkage module, start on a random parental chromosome and switch chromosomes between adjacent loci with probability $r_{link} = 0.15$. Modules assort independently. The offspring gets (maternal gamete, paternal gamete).
- **Mutation:** each allele mutates with probability $\mu = 0.02\times\text{mutation modifier}$: $a' = \mathrm{clip}(a + \mathcal N(0, 0.05))$. 5% of mutations are **large-effect**, with $\sigma = 0.2$.
- **Genetic distance:**

$$
\delta(i,j) = \sqrt{\frac{\sum_k w_k\,(g_{ik} - g_{jk})^2}{\sum_k w_k}}
$$

  It is computed over genotypic values. Neutral markers and instinct loci are weighted 1, and trait loci are weighted by their phenotypic effect size.
- **Reproductive isolation:** fertility falls with $F_{compat}$ (§5.10). The default $\delta_{iso} = 0.22$ is tunable per preset; experiment worlds lower it to speed up speciation.
- **Heritability** is below 1 because of developmental noise ([04 §4.2](04-organism-model.md)). The realized $h^2$ is estimated by parent–offspring regression in analysis.

---

## 5.12 Speciation and phylogeny (`SpeciesClusterer`, `SpeciesRegistry`, `PhylogeneticTree`)

- **Every 24 ticks**, living organisms are clustered by leader clustering against the current species representatives (medoids):
  - an organism joins the nearest species if $\delta < \delta_{sp}$ (default 0.15);
  - otherwise it seeds a candidate cluster.
- **Hysteresis:** a candidate becomes a registered species only if it persists for **2 consecutive rounds with ≥ 3 members**. This prevents flicker.
- **Parentage:** a new species' parent is the species that most of its members' parents belonged to. This produces a **phylogenetic tree** with origin and extinction ticks.
- A species with no living members is marked **extinct** (an event).
- **Naming** (`SpeciesNamer`): an adjective from the centroid's coat hue and pattern plus a noun from its niche (diet × size × locomotion). Examples: "Ashback Grazer", "Dusk-striped Stalker", "Reedfoot Wader". A counter disambiguates collisions.
- Species colors in the replay come from a hue family inherited from the parent species, so a clade looks related.

---

## 5.13 Disease (`TransmissionModel`, `StrainEvolution`)

The model is individual-based **SEIR** with evolving strains.

| Strain parameter | Meaning |
| --- | --- |
| $\beta$ | Transmission probability per contact per tick |
| $\tau_E$, $\tau_I$ | Mean latent and infectious durations (geometric) |
| $v$ | Virulence: health damage and energy drain per tick while infectious |
| $\sigma_{env}$, $t_{1/2,env}$ | Shedding into the environment (water, mud) and persistence there |
| $\delta_{host}$ | Host range: infects hosts within this genetic distance of its origin species' centroid |
| $\tau_R$ | Duration of immunity |

**Transmission:**

$$
p_{inf,i} = 1 - \prod_{j\,\in\,\text{infectious adjacent}}\big(1 - \beta_j s_i\big)\cdot\big(1 - \beta_{env}\,P_{env}(x_i)\,s_i\,[\text{drank or wallowed}]\big)
$$

$$s_i = (1 - 0.8\,\text{immune investment})(1 + 0.5\,\text{stress})(1 - \text{immunity}_i)$$

- **Progression:** E → I after $\tau_E$. I → R with rate $(1/\tau_I)(1 + \text{immune investment})$. Health reaching 0 while infectious is death by **disease**. R → S after $\tau_R$.
- **Virulence–transmission trade-off:** $\beta = \beta_{max}\,v/(v + v_{half})$. On each transmission, with probability $\mu_p$ the strain mutates, $v' = v\,e^{\mathcal N(0, 0.1)}$. **Virulence evolves.**
- **Visible signs:** infectious animals are described as "looks sick, coughing", so avoidance of the sick can emerge.
- **Waterholes** accumulate environmental pathogen. Drought concentrates animals and raises transmission.
- Carcasses of infected animals stay infectious for $t_{1/2,env}$.

**Parasites** (ectoparasites): load grows with the number of conspecifics within 1 patch. `groom_X` (−0.2 for X), self-grooming (−0.08) and `wallow` (−0.15) reduce it. The energy drain is $0.1 \times \text{load} \times B$. This makes social grooming genuinely useful.

---

## 5.14 Social rules

| Rule | Model |
| --- | --- |
| **Contests** (`challenge_X`) | If X chooses `submit_to_P` or flees, the challenger wins without a fight. If both display (`threat_display`), the winner is decided by resource-holding potential $RHP = m^{0.66}(0.5 + w)\,H\,(1 + 0.2\,\text{ornament}) + \text{noise}$, with no injury. If either chooses `attack`, they fight (§5.9). The Elo ratings update, and the loser gets `recently_defeated` for 24 ticks |
| **Dominance benefits** | Priority in contested food splits (§5.5); the dominance relation appears in rivals' states |
| **Territory** | `scent_mark` creates a `TerritoryMark` with strength 1 and a half-life of 3 days. Intruders perceive "the scent mark of a rival of your kind" |
| **Grooming** | `groom_X` lowers X's parasites and stress, and raises the bond for both |
| **Food sharing** | `share_food_with_X` transfers carried food, or tolerates co-feeding at a carcass |
| **Alarm calls** | Benefit listeners next tick; cost the caller detectability |
| **Kin selection** | Relatedness $r$ is recorded, and analysis tests Hamilton's rule ($rB > C$) on sharing, alarm and defense events |

---

## 5.15 Death

Death is **never an action**. The reference design's `DIE` is removed. `MortalityJudge` checks the following each tick in `LifecyclePhase`. When health reaches 0, the cause is taken from the `DamageLedger` as the largest damage source over the last 3 ticks.

| Cause | Trigger | Notes |
| --- | --- | --- |
| Starvation | $E = 0$ and mass $< 0.6\times$ lean mass, or health 0 from starvation damage | `orphaned` flag for unweaned young |
| Dehydration | $h = 0$ for 2 ticks | |
| Predation | killed by a heterospecific | Records the killer id and species |
| Combat | killed by a conspecific | Contests, infanticide |
| Disease | health 0 while infectious | Records the strain id |
| Senescence | Gompertz–Makeham hazard (below) | |
| Hypothermia / Hyperthermia | health 0 from thermal damage | |
| Toxin | toxin load ≥ lethal dose $\times (1 + 2\,\text{resistance})$ | |
| Drowning | deep water with swim skill < 0.5, or an exhausted swimmer: 50% per tick | |
| Fire | burning patch: damage 0.4 × intensity per tick | |
| Disaster | lava or eruption zone | |
| Birth complications | §5.10 | |

**Aging (Gompertz–Makeham):**

$$\mu(a) = \lambda_M + \alpha\,e^{\gamma a/\mathcal L}, \qquad P(\text{death this tick}) = 1 - e^{-\mu(a)}$$

The defaults $\lambda_M = 10^{-5}$, $\alpha = 2\times10^{-5}$ and $\gamma = 6$ put the median age at death from senescence near $\mathcal L$.

**After death:** a `Carcass` is created with mass $0.6\,m$, infection state and species of origin. It decays ([03 §3.10](03-world-model.md)), feeds scavengers, invertebrates and soil, and emits `carrion` scent.

---

## 5.16 Population regulation and calibration

**Regulating forces (all emergent):** food limitation (bottom-up), predation (top-down), density-dependent disease and parasites, territorial exclusion, and stress.

**Calibration protocol** (`lifeform calibrate <preset>`):

1. **Analytic pass.** For each founder archetype, compute the field metabolic rate (about 2.5 B) and the food needed per tick, $\mathrm{FMR}/(\mathrm{ED}_f\,e_f)$.
2. **Primary productivity scale $\psi$.** Choose $\psi$ so that the seasonally averaged sustainable yield of each food layer ($\sum r K g_{env}/4$ over patches) × a harvest reachability of 0.4 supports the preset's target herbivore count $N^*_{herb}$ (typically 60–110).
3. **Predators.** With 10% trophic transfer efficiency (Lindeman), the expected predator count is $N^*_{pred} \approx 0.1\cdot\text{prey production}/\mathrm{FMR}_{pred}$. For the default presets that is about 8–15, a realistic ratio.
4. **Jev pilot.** Run 200 ticks with real Jev (about $1–2), measure realized intake and population trend, and rescale $\psi$ once by the ratio. The result is written to `presets/<name>.calibration.yaml`.

**Safety rails (none of them cull):**

- `max_population` (default 300) pauses the run (see [02 §2.13](02-architecture.md)).
- The optional `immigration` intervention (**off** by default) adds a founder-like migrant every N ticks at a random suitable patch. It is recorded in the manifest as an intervention, so any analysis can exclude it.

---

## 5.17 Phenomena we expect to observe, and how we will measure them

| Phenomenon | Mechanism in Lifeform | Best world | Metric |
| --- | --- | --- | --- |
| Lotka–Volterra cycles | Predator–prey feedback | Red Queen Pit | Phase portrait; period from autocorrelation |
| Selfish herd | Dilution and confusion; `herd_cohesion` | Serengeti Pulse | Nearest-neighbor distance with and without predators in view |
| Migration following green-up | Seasonal grass pulse; spatial memory; `migration_urge` | Serengeti Pulse | Herd centroid lag behind the NDVI-like grass peak |
| Bergmann's rule | Thermoregulation costs | Boreal Long Night; Spine of the World | Regression of mean $M_\infty$ on mean temperature |
| Nocturnality shift | Daytime heat and water loss | Oasis of Salt | `activity_phase` trajectory |
| Aposematism | Toxicity plus predator learning (Rescorla–Wagner) | Emerald Canopy | Correlation of toxicity and ornament; attack rate on toxic prey over time |
| Adaptive radiation | Island-specific food | Galápagos Scatter | Diet-simplex divergence between islands |
| Allopatric speciation | Rift isolation | The Sundering | $\delta$ between sides over time; speciation events |
| Red Queen arms race | Coevolution | Red Queen Pit | Prey speed and vigilance versus predator speed and crypsis |
| Virulence evolution | Trade-off plus strain mutation | Pale Plague Meadow | Mean strain $v$ over time |
| Island dwarfism or gigantism | Resource limits, predator release | Galápagos Scatter | $M_\infty$ versus founders |
| Regressive evolution | Cost of eyes without light | Lightless Hollows | `visual_acuity` decline; `olfaction` rise |
| r/K shift | Disturbance frequency | Ashfall Caldera versus Emerald Canopy | `offspring_investment` |
| Ideal free distribution | Foragers matching resource density | Any | Forager density versus patch productivity |
| Kin altruism | Alarm, sharing, defense | Serengeti Pulse | Event rates by relatedness |
| Trophic cascade | Predator removal (experimental toggle) | Serengeti Pulse A/B | Vegetation biomass with and without predators |
| Overgrazing collapse and recovery | Logistic regrowth with low-biomass penalty | Oasis of Salt | Local grass time series |
| Fire–grazing interaction | Post-fire flush | Serengeti Pulse | Grazer density on burn scars |
