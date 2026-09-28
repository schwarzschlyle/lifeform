# 06 — Action Catalog

---

## 6.1 Principles

1. **Primitive verbs, grounded targets.** There are no macro-behaviors like `find_food()` or `avoid_predator()`. Foraging trips, hunts, migrations and herding are *sequences* of primitive choices made tick by tick by Jev.
2. **Affordances, not free text.** Each tick, code builds a menu of concrete, legal options (verb × target or direction), such as `flee_from_P1`, `graze_here` or `go_to_water_memory_2`. Jev picks one. An illegal option can never be chosen because it never appears.
3. **Execution is physics.** When Jev picks `approach_P3`, code's `LocalPlanner` works out which patch to step into. That is motor control, not decision-making. Code never replaces the chosen verb (rule J12).
4. **Two channels, like real animals.** Each tick has a **body action** and, in parallel, a **vocal signal**. An animal can flee *and* scream.
5. **Death is not an action.** The reference design's `DIE` is removed.

---

## 6.2 How one Jev call becomes behavior

| Jev answer ([07](07-jev-nervous-system.md)) | Becomes |
| --- | --- |
| `action` (Choice over affordances) | the body verb and its target, **sampled** from the distribution sharpened by the `decisiveness` gene |
| `effort` (Score 0–3) | the effort level: speed, energy cost, noise, stamina, force |
| `threat` (Score 0–4) | fear-state update (appraisal) |
| `call` (Choice) | the vocal signal this tick |
| `focus` (Choice over percepts) | the attention target: a learning-rate bonus, and the gaze line drawn in the replay |
| `action.confidence` | decisive, hesitant or dithering execution (§6.8) |

---

## 6.3 Verb catalog

PAL is the physical activity level: activity energy is $B\cdot(\mathrm{PAL}-1)$ before effort scaling ([05 §5.2](05-ecology-rules.md)). "Menu key" is the template for the Choice option name.

### Locomotion

| Verb | Menu key | Legal when | Execution | PAL | Replay visual |
| --- | --- | --- | --- | --- | --- |
| `move` | `move_{north…northwest}` | the next patch in that heading is passable for this body | Up to $n_{steps}(\text{effort})$ patches along the heading; the local planner skirts obstacles | 1.5 | Glide with a fading trail |
| `approach` | `approach_{P#/C#/sound#}` | the target is perceived | Steps toward the target's *current* position, recomputed each sub-step | 1.5 | Trail; a gaze line to the target |
| `flee` | `flee_from_{P#/fire/sound#}` | a threat is perceived | Steps that maximize distance from the threat. Cover and refuge patches score higher when the organism can use them | 2.0 | Motion streak |
| `follow` | `follow_{P#}` | a conspecific is perceived | Keeps within 1–2 patches of the target | 1.5 | Thin tether line |
| `stay_with_group` | `stay_with_group` | 2+ conspecifics within vision | Moves toward the group centroid | 1.4 | — |
| `go_to_memory` | `go_to_{kind}_memory_{k}` | a spatial memory exists | A* toward the remembered place (radius-limited; recomputed each tick) | 1.5 | Faint dotted path |
| `follow_scent` | `follow_scent_{channel}` | the scent channel is perceived | Climbs the gradient (upwind) | 1.5 | Scent wisps |
| `stalk` | `stalk_{P#}` | the target is perceived | At most 1 patch per tick, detectability × 0.5, no footstep noise | 1.6 | Low, slow crouch |
| `chase` | `chase_{P#}` | the target is perceived and within $2v_{max}$ | Pursuit at effort speed, striking if adjacent at the end | 2.5 | Speed lines |
| `climb` / `descend` | `climb_tree` / `climb_down` | forest or rainforest patch, climb skill ≥ 0.3, mass ≤ 60 kg | Toggles the `climbing` condition | 2.0 | Sprite lifts; canopy shadow |
| `enter_den` / `leave_den` | `enter_den` / `leave_den` | on its own den patch (or an unoccupied den) | Toggles the `in_den` condition | 1.1 | Sinks into a burrow icon |

### Foraging and ingestion

| Verb | Menu key | Legal when | Execution | PAL | Visual |
| --- | --- | --- | --- | --- | --- |
| `graze` | `graze_here` | grass on the patch ≥ one bite; fiber diet weight ≥ 0.1 | Bite model on grass | 1.5 | Nibble pulse; grass tint fades |
| `browse` | `browse_here` | browse ≥ one bite; fiber weight ≥ 0.1 | Bite model on browse | 1.5 | Nibble pulse |
| `eat_fruit` | `eat_fruit_here` | fruit ≥ one bite; soft-plant weight ≥ 0.1 | Bite model on fruit | 1.4 | Small fruit pops |
| `forage_seeds` | `forage_seeds_here` | seeds ≥ one bite | Bite model on seeds | 1.5 | Pecking |
| `dig_for_grubs` | `dig_for_grubs_here` | invertebrates present; animal weight ≥ 0.1 | Bite model × dig skill | 1.8 | Dirt puffs |
| `feed_on_algae` | `feed_on_algae_here` | shallow water with algae | Bite model on algae | 1.5 | Ripples |
| `eat_fungi` | `eat_fungi_here` | fungi present | Bite model on fungi | 1.3 | — |
| `eat_carcass` | `eat_carcass_{C#}` | the carcass is on or adjacent to the patch; animal weight ≥ 0.1 | Bite model on meat; contested split | 1.6 | Tearing jitter |
| `drink` | `drink` | a drinkable patch here or adjacent | Water intake | 1.2 | Water ripple rings |
| `carry_food` | `carry_food_from_{C#/here}` | edible food here; chunk ≤ 0.15 m | Picks up a chunk (condition `carrying_food`) | 1.5 | Small item at the mouth |
| `cache_food` | `cache_food` | carrying | Creates or extends a `FoodCache` here | 1.2 | Buried marker |
| `drop_food` | `drop_food` | carrying | Leaves the chunk on the patch | 1.0 | — |
| `steal_food` | `steal_food_from_{P#}` | the target is adjacent and carrying or eating | A contest by RHP; the winner gets the food | 2.5 | Scuffle flash |

### Predation and combat

| Verb | Menu key | Legal when | Execution | PAL | Visual |
| --- | --- | --- | --- | --- | --- |
| `attack` | `attack_{P#}` | the target is an animal within reach this tick ($\le n_{steps}+1$) | Moves in, strikes if adjacent ([05 §5.9](05-ecology-rules.md)) | 4.0 | Red arc flash; impact particles |
| `ambush` | `ambush` | on a patch with cover ≥ 0.3 or hidden | Stays hidden (detectability × 0.3). Its execution rule is to **strike the first animal of another species, smaller than itself, that ends a movement sub-step adjacent** | 1.2 | Dim silhouette, then a pounce |
| `fight_back` | `fight_back_{P#}` | P# attacked it last tick and is adjacent | Counter-strike without moving | 3.5 | Clash flash |
| `brace` | `brace` | always | Defensive stance: the brace term in $P_{hit}$ and counter-strikes | 1.5 | Hunched outline |
| `threat_display` | `threat_display_at_{P#}` | the target is within 3 patches | Intimidation. Shown in the target's next state as "P# bares its teeth and puffs up at you". Counts as a display in contests | 1.8 | Puff-up scale pulse |
| `mob` | `mob_{P#}` | the target is heterospecific and adjacent, and 1+ conspecific allies are within 2 | Small damage, and the target becomes `harassed` | 2.5 | Swarm jitter |
| `challenge` | `challenge_{P#}` | the target is a conspecific within 2 patches | Dominance contest ([05 §5.14](05-ecology-rules.md)) | 2.0 | Face-off glyph |
| `submit` | `submit_to_{P#}` | a conspecific is within 3 patches | Ends a contest as the loser, with no injury | 1.0 | Shrink and dim |

### Concealment and vigilance

| Verb | Menu key | Legal when | Execution | PAL | Visual |
| --- | --- | --- | --- | --- | --- |
| `hide` | `hide` | cover ≥ 0.3 here, or in a den | Detectability × (1 − 0.8 · cover) and the `hidden` condition | 1.1 | Fade to 40% opacity |
| `freeze` | `freeze` | always | Motion factor 0.5, no noise | 1.0 | Stillness; a subtle outline shimmer |
| `play_dead` | `play_dead` | a predator is adjacent or it was attacked this tick | Described to others as "lying limp, seems dead" | 1.0 | Tipped-over sprite |
| `scan_surroundings` | `scan_surroundings` | always | +30% vision radius and +0.2 certainty next tick; sentinel role | 1.2 | Rotating scan cone |
| `investigate` | `investigate_{P#/C#/sound#}` | an uncertain percept or sound | Approaches to within 2 patches; certainty +0.25 next tick | 1.4 | "?" glyph, cautious path |

### Rest and body care

| Verb | Menu key | Legal when | Execution | PAL | Visual |
| --- | --- | --- | --- | --- | --- |
| `rest` | `rest` | always | Healing × 2; stamina recovers | 1.1 | Gentle breathing pulse |
| `sleep` | `sleep` | always | The `asleep` condition. Touch, attack or a sound above 25 dB over threshold **wakes** it physiologically, and it decides again next tick | 0.9 | Dim, curled up; soft "z" particles |
| `bask` | `bask` | sunlit patch, $L > 0.5$ | Solar gain for ectotherms | 1.0 | Warm glow |
| `seek_shade` | `seek_shade` | shade (canopy ≥ 0.4 or rock) here or adjacent | Moves there, then rests cooler | 1.2 | Cool tint |
| `huddle` | `huddle_with_group` | 1+ conspecific adjacent | Conductance × 0.7 for all huddlers | 1.0 | Sprites nestle together |
| `wallow` | `wallow` | mud (wetland) or shallow water | Cooling; parasites −0.15 | 1.3 | Mud splash |
| `groom_self` | `groom_self` | always | Parasites −0.08 | 1.1 | Small shake |
| `dig_den` | `dig_den` | dig skill ≥ 0.3 and diggable terrain | 3 ticks of accumulated work creates a `Den` | 2.5 | Dirt-mound progress ring |

### Social

| Verb | Menu key | Legal when | Execution | PAL | Visual |
| --- | --- | --- | --- | --- | --- |
| `groom` | `groom_{P#}` | the conspecific is adjacent | Their parasites −0.2 and stress down; bond up for both | 1.2 | Heart-shaped sparkle |
| `share_food` | `share_food_with_{P#}` | carrying food or at a carcass; the target is adjacent | Transfers or tolerates co-feeding | 1.1 | Item hand-off arc |
| `scent_mark` | `scent_mark` | always | Creates a `TerritoryMark` | 1.2 | Colored dot that fades |

### Reproduction and care

| Verb | Menu key | Legal when | Execution | PAL | Visual |
| --- | --- | --- | --- | --- | --- |
| `court` | `court_{P#}` | both eligible ([05 §5.10](05-ecology-rules.md)); within 2 patches | Display; sets `courted_by` on the target | 2.0 | Display plumes |
| `mate_with` | `mate_with_{P#}` | the chooser was courted by P# within 2 ticks; adjacent after movement | Conception roll | 2.0 | Paired pulse |
| `nurse` | `nurse_{P#}` | lactating; its own dependent young are adjacent | Milk transfer | 1.3 | Soft glow link |
| `suckle` | `suckle` | dependent; mother adjacent and lactating | Receives milk (half rate unless the mother nurses) | 1.0 | — |
| `defend_young` | `defend_young` | its own dependent young within 2 patches | Stays adjacent, braced; it takes hits aimed at the young first | 1.5 | Shield ring |

**Totals:** 55 body verbs in 7 families (13 locomotion, 13 foraging, 8 combat, 5 concealment, 8 body care, 3 social, 5 reproduction; `climb`/`descend` and `enter_den`/`leave_den` count separately), plus the `stalled` outcome (the organism does nothing), which is not a verb and is only used when a Jev call fails permanently (rule J12).

---

## 6.4 Call catalog (vocal channel)

| Call | Menu key | Legal when | Effect | Source level |
| --- | --- | --- | --- | --- |
| Silent | `silent` | always | — | — |
| Alarm call | `alarm_call` | vocal capacity ≥ 0.2 | Conspecifics hear "alarm call from your kind, {loudness}, {direction}" | 70 dB × $m^{0.3}$ factor |
| Food call | `food_call` | vocal capacity ≥ 0.2 | Recruits group and kin to food | 60 dB |
| Mating call | `mating_call` | adult | Eligible opposite-sex conspecifics hear it; detectability +50% | 75 dB |
| Contact call | `contact_call` | always (including young) | Group cohesion; mother and young find each other | 50 dB |
| Distress call | `distress_call` | always (including young) | "your kin is screaming for help" to relatives; predators also hear it | 80 dB |
| Warning growl | `warning_growl` | vocal capacity ≥ 0.2 | Directed deterrence; appears in the target's state | 65 dB |
| Territorial call | `territorial_call` | adult, vocal capacity ≥ 0.4 | Advertises the territory to rivals | 70 dB |

Every non-silent call adds PAL +0.2 and makes the caller more detectable to anything that hears it, including predators. Honest signaling has a cost.

---

## 6.5 Effort levels

`effort` is Jev's Score answer. The level used is the **rounded expected score**, then lowered by hesitation (§6.8).

| Level | Name | Movement steps | Energy factor $\eta$ | Noise | Stamina | Strike force |
| --- | --- | --- | --- | --- | --- | --- |
| 0 | minimal | $\min(1, v_{max})$ | 0.9 | silent | +0.2 per tick | × 0.8 |
| 1 | steady | $\lceil 0.5\,v_{max}\rceil$ | 1.0 | quiet | +0.2 per tick | × 1.0 |
| 2 | hurried | $\lceil 0.75\,v_{max}\rceil$ | 1.25 | footsteps | −0.15 per tick | × 1.1 |
| 3 | all-out | $v_{max}$ | 1.7 | loud footsteps | $-1/\text{stamina ticks}$ | × 1.25 |

Because Jev answers `effort` in isolation from `action`, effort reads the **situation's urgency**: a calm afternoon gets minimal effort, and a charging predator gets all-out. That is the reference design's *urgency* variable $U$, supplied by Jev.

---

## 6.6 Affordance generation (`AffordanceGenerator`)

Rules are composable **specifications** (`AffordanceRule`). Each rule yields candidate `Affordance(key, verb, target, description, relevance)` objects.

1. **Core set (always offered):** `rest`, `sleep`, `scan_surroundings`, `freeze`, the passable `move_{dir}` headings, `brace`. `hide` is added when cover allows.
2. **Here-patch rules:** food verbs for layers that are present *and* digestible by this diet (a pure carnivore is never offered `graze_here`); `drink`; `bask`, `seek_shade`, `wallow`, `huddle`, `dig_den`, `enter_den`, `climb_tree`; `groom_self`, `scent_mark`.
3. **Entity rules**, for each of the top-$k$ salient entities ($k$ = attention span 4–7):
   - **Other species:** `approach`, `flee_from`, `investigate` (if certainty < 0.7), `attack` and `chase` (if within reach), `stalk`, `threat_display_at`, `mob` (if allies are present).
   - **Conspecifics:** `follow`, `groom`, `court`, `mate_with`, `challenge`, `submit_to`, `share_food_with`, `steal_food_from`, `nurse`.
   - **Carcass:** `approach`, `eat_carcass`, `carry_food_from`.
   - **Current attacker:** `fight_back`, `play_dead`.
4. **Smell rules:** `follow_scent_{channel}` for the top 2 attractive scents; `flee_from_smoke` for smoke.
5. **Sound rules:** `investigate_sound#` or `flee_from_sound#` for the top 2 sounds.
6. **Memory rules:** `go_to_{kind}_memory_{k}` for the top 3 memories by need match (water when thirsty, a den when tired or cold, a refuge when afraid).
7. **Condition rules:** `climb_down`, `leave_den`, `cache_food`, `drop_food`, `suckle`, `defend_young`.

**Cap:** 32 options. The core set is always kept. The rest are ranked by a **relevance score** = need match (hunger for food verbs, thirst for water, and so on) + proximity + threat relevance. Only the top entries are kept.

**Relevance filtering is attention, not choice.** It decides what is on the menu, never what is picked. The full candidate list and the pruned entries are recorded for audit.

**Option order** is shuffled per call by the seeded decision stream, which neutralizes any positional bias. The Question Lab measures whether such bias exists ([07 §7.11](07-jev-nervous-system.md)).

**Descriptions state their code-computed consequences** (design rule J3):

- `flee_to_forest_west`: "run into the forest to the west: cover, and P1 is slower among trees"
- `attack_P4`: "attack P4 (a smaller plant-eater, adjacent, has not noticed you)"
- `drink`: "drink from the pond beside you"

---

## 6.7 Resolution order and conflicts

All organisms decide on the same snapshot. Resolution then runs in this order:

1. **Signals** (`SignalPhase`): calls become `SoundEvent`s (heard next tick); scent marks are placed.
2. **Posture changes** (`MovementPhase` pre-step): sleep, rest, hide, freeze, brace, climb, den entry and exit, and ambush are applied first, so they count during strikes.
3. **Movement sub-steps** (`SubStepMover`):
   - **Initiative order:** sort movers by (effort level ↓, agility ↓, seeded random tie-break).
   - For sub-step $s = 1 \ldots 5$: each mover with steps remaining moves one patch in initiative order. The `LocalPlanner` re-targets each sub-step from the target's *current* position, so **pursuit emerges** from speed differences.
   - The `OccupancyLedger` enforces patch capacity ([03 §3.1](03-world-model.md)). A blocked mover tries the two neighboring headings, then waits that sub-step.
   - `ambush` triggers when a qualifying animal ends a sub-step adjacent to the ambusher.
4. **Interactions** (`InteractionPhase`), in order: strikes (by initiative; an animal killed earlier in the tick does not strike), then contests, mating, grooming, nursing, sharing and stealing.
5. **Consumption** (`ConsumptionPhase`): eating and drinking, with contested patches and carcasses split by dominance and mass ([05 §5.5](05-ecology-rules.md)).
6. **Failure outcomes:** a target that died, left reach, or a resource that ran out gives the outcome `failed:<reason>`. The energy is still spent. The failure appears in the next state's recent history: "you tried to eat, but the carcass was gone".

---

## 6.8 Execution modulated by confidence (decisive, hesitant, dithering)

Jev's `action.confidence` $c$ is calibrated. The organism's heritable `caution` gene sets two thresholds:

$$c_{low} = 0.25 + 0.2\cdot\text{caution},\qquad c_{high} = 0.60 + 0.2\cdot\text{caution}$$

Let *urgent* mean the rounded threat score is 3 or higher.

| Band | Rule | Replay visual |
| --- | --- | --- |
| $c \ge c_{high}$ — **decisive** | Execute as chosen | Bright halo |
| $c_{low} \le c < c_{high}$ — **hesitant** | Effort −1 level (min 0), **unless urgent** | Soft halo |
| $c < c_{low}$ — **dithering** | Effort −1 and at most 1 patch of movement, **unless urgent**. "Paused to look": +0.15 perception certainty next tick | "?" glyph |

This maps the reference design's confidence × urgency matrix without an LLM:

| | Low urgency | High urgency |
| --- | --- | --- |
| **High confidence** | act (decisive) | act immediately (decisive) |
| **Low confidence** | act tentatively and gather information (dithering) | **act anyway** (the urgency override) |

The verb is never changed, only *how* it is carried out. Because $c \approx p_{max}$ for large menus but not for small ones ([01 §1.4](01-jev-research.md)), the thresholds are **re-fitted per menu-size band** from Question Lab data before the first real run.
