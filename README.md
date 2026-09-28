# Lifeform

A 2D artificial ecology where **every animal's every action comes from one Jev call per tick**. Code computes the
world (climate, water, plants, scent, sound, metabolism, predation, reproduction, disease, genetics, speciation); Jev
chooses what each animal does. Runs are recorded and replayed in a browser theater.

The full design is in [PLAN.md](PLAN.md) and [docs/plan/](docs/plan/).

## Setup

Python 3.12 or newer, and Node 20 or newer for the theater.

```bash
python3 -m venv .venv
.venv/bin/pip install -e ".[dev]"
cd web && npm install && npm run build && cd ..
```

## Running a simulation

Every run shows a cost estimate and asks for confirmation before anything is spent. The API key is requested at that
point (input hidden, kept in memory only, never written to disk) unless `TYPESAFE_API_KEY` is already set.

```bash
.venv/bin/lifeform worlds                                   # the 14 world settings
.venv/bin/lifeform estimate all                             # calls, cost and wall time for all 12 core worlds
.venv/bin/lifeform preflight                                # checks the key, the pinned model and one call's latency
.venv/bin/lifeform run serengeti-pulse --ticks 300 --population-scale 0.5 --max-usd 2
```

How much simulation you get is set by these options:

| Option | Effect |
| --- | --- |
| `WORLDS...` | One or more world slugs, `all` (12 core worlds) or `everything` (plus 2 stretch worlds) |
| `--ticks` | Ticks per world (1 tick = 2 simulated hours; the default is each preset's length) |
| `--population-scale` | Multiplies founders and population targets; calls scale roughly linearly with it |
| `--max-usd` / `--max-calls` | Hard budget: the run stops cleanly before crossing it |
| `--decision-detail` | `full` records the exact state sent to Jev for the Mind Inspector; `summary` or `none` save disk |
| `--brain` | `jev`, `kev` or `heuristic` for this run (default: the active brain in `brains.yaml`). `heuristic` is a free offline stand-in stamped "not Jev" everywhere |
| `--yes` | Skip the confirmation prompt |

A tick costs one call per living animal. At the published 1,200 requests/minute, 100 animals take about 5 seconds per
tick; the rate limit, not the price, sets the pace.

## Choosing the brain: Jev or Kev

Lifeform talks to its brain through TypeSafe's System One protocol. [Kev](https://github.com/jaredpalmer/kev), an
open Jev-style model you serve yourself, speaks the same protocol, so either one can decide for the animals. Nothing
else changes: one call per animal per tick, the same five questions, the same recording.

`brains.yaml` lists the brains and which one is active (`active: jev`). Switch the default, or override it per
command:

```bash
.venv/bin/lifeform brain                 # show jev, kev and heuristic, and which is active
.venv/bin/lifeform brain kev             # make Kev the default (edits brains.yaml); `lifeform brain jev` switches back
.venv/bin/lifeform run red-queen-pit --brain jev --ticks 10    # use Jev for this run only
```

Kev needs a running Kev server. By default Lifeform expects one at `http://127.0.0.1:8009`:

```bash
cd ../kev && uv sync --extra serve
uv run --extra serve python -m kev.serve --run jaredpalmer/kev-4b --port 8009
```

Kev-4B wants a CUDA GPU, or a 32 GB Apple Silicon Mac. On a machine without either, deploy it on Modal instead
(see `kev/skills/kev-deploy`). Then set `base_url` under `kev` in `brains.yaml` to the https address, export
`KEV_API_KEY` with the endpoint's key, and set `host_usd_per_hour` to the GPU price (for example 1.95 for an L40S), so
that estimates and `--max-usd` include hosting. `lifeform preflight --brain kev` checks the server and prints which
checkpoint it serves.

Things to know about Kev:

- Kev was trained on states of up to 384 tokens. Lifeform sends 600–900-token states with menus of up to 32 options,
  so expect weaker choices than Jev, especially from Kev-0.8B and Kev-4B. Kev-27B handles long inputs best.
- The hesitation thresholds were tuned against Jev's calibration. Kev's confidences are calibrated differently, so
  Kev animals may hesitate more or less often.
- Each run records which brain made it and the checkpoint the server reported, and the theater labels Kev runs
  "Kev". Results from the two brains are never mixed.

## Watching a run

```bash
.venv/bin/lifeform serve          # then open http://127.0.0.1:8765
```

- The landing page explains the whole project from the code itself (served by `/api/catalog`): what Jev is, its
  role, the five questions word for word, a real recorded call, the tick pipeline, all 10 founding species with every
  derived attribute and gene, the genome, all actions and calls, the ecology models, terrain, food layers and the 14
  worlds. Sections have shareable links such as `#/species`, `#/jev` or `#/worlds`.
- Drag to pan, scroll to zoom. The world is a torus, so it wraps seamlessly.
- Click an animal to open the **Mind Inspector**: its vitals, what Jev was shown, the probability of every option on
  its menu (▶ sampled, ★ Jev's top choice), and its confidence, threat, effort, call and focus.
- Keys: `space` play/pause, `←/→` step (hold `shift` for a day), `[ ]` speed, `f` follow, `esc` deselect.
- Deep links: `#/run/<run-id>/<world>@<tick>:<animal-id>` opens a world at a tick with an animal selected.
- Runs in progress refresh every 15 seconds.

For theater development, `cd web && npm run dev` serves on port 5173 and proxies `/api` to `lifeform serve`.

## Quality checks

```bash
.venv/bin/ruff check src tests && .venv/bin/mypy && .venv/bin/pytest
cd web && npm run typecheck
```

`tests/contract/test_jev_adapter.py` drives the real `typesafe-sdk` through a mocked HTTP transport: request shape,
authorization, the pinned model, answer decoding, retrying 429s and failing fast on a rejected key. The `live` test runs
one real tick when `TYPESAFE_API_KEY` is set.

## Implementation status

| Area | Status |
| --- | --- |
| World: torus grid, 13 terrains, 7 food layers, climate, weather, hydrology, scent, sound, fire, floods, droughts, eruptions, rifts, rafting, epidemics | Implemented |
| Organisms: 89-locus diploid genome, 24 heritable instincts, allometric phenotype, physiology, drives, memory, Rescorla–Wagner learning, kinship, dominance | Implemented |
| Jev nervous system: words-only mind state, ≤ 32 grounded affordances, 5-question panel in one call, decisiveness sampling, hesitation bands, rate governor, retry-not-substitute | Implemented |
| Ecology: foraging, predation, pursuit, contests, courtship with consent, pregnancy, nursing, weaning, disease, death causes, decomposition, speciation | Implemented |
| CLI with cost estimate, confirmation, hidden key prompt and hard budget | Implemented |
| Recording, replay server and theater (terrain, creatures, weather, effects, inspector, charts, timeline) | Implemented |
| Checkpoint and resume, re-simulation from the decision tape, `calibrate`, Question Lab, cinematic director, clip export | Next milestones |

Balance note: the ecological coefficients were tuned offline with the heuristic stand-in, which forages poorly.
Expect to retune (see `presets/` and `src/lifeform/config/parameters.py`) once real Jev runs show how animals behave.
