# 01 — Jev: What It Is, What It Can Do, and How Lifeform Uses It

Research date: 2026-09-26. API facts were checked against the installed `typesafe-sdk 0.7.1` source and TypeSafe's documentation. Anything marked *vendor-reported* has not been measured by us yet. Milestone M0 measures it (see [10](10-analysis-testing-roadmap.md)).

---

## 1.1 Summary

Jev is TypeSafe AI's first **System One model**, launched on 2026-09-15. It is named after the economist William Stanley Jevons, and "System One" refers to Kahneman's fast, intuitive mode of thinking. Jev does not generate text. You send it:

- a **state**: text, a JSON object, or an array of text describing a situation; and
- a set of named, typed **questions**.

It returns **calibrated, typed answers**: probabilities, a choice with its full distribution, or an expected score. All questions in a request are evaluated **in parallel and in isolation** against the same state. Adding questions costs input tokens but adds almost no latency.

That shape fits the nervous system of a simulated animal almost exactly:

| Animal nervous system | Jev |
| --- | --- |
| Senses and body signals produce a moment of experience | `state` (what this animal perceives, feels and remembers) |
| Several judgments made at once (what to do, how dangerous, how hard to try, what to call out, what to attend to) | Several typed questions in **one** call |
| Behavior is probabilistic, and some choices are clearer than others | `probabilities` and `confidence` on every Choice and Score |
| Fast and cheap enough to run for every animal every moment | ~100 ms median (*vendor-reported*), $0.042 per million input tokens, free output |

Jev only chooses. Everything countable, measurable or physical is computed by code. Lifeform's central rule is **"Code computes, Jev chooses."**

---

## 1.2 API surface (verified against `typesafe-sdk 0.7.1`)

### Client

| Item | Detail |
| --- | --- |
| Package | `typesafe-sdk` (PyPI), import `typesafe_sdk`, MIT license, Python ≥ 3.10, depends on `httpx2`, `pydantic ≥ 2.12`, `tenacity` |
| Clients | `TypeSafeClient` (sync) and `AsyncTypeSafeClient` (async); both work as context managers |
| Constructor | `AsyncTypeSafeClient(api_key=None, model=None, retry=None, timeout=None, headers=None, transport=None, http_client=None, base_url=None)` |
| Main call | `await client.system_one(state, questions, *, model=None, retry=None, timeout=None, extra_headers=None, extra_body=None, response_model=None)` |
| Model listing | `await client.models.list()` returns `ListModelsResponse(models=(ModelMetadata(name, description, release_date), ...))` |
| Environment | `TYPESAFE_API_KEY`, `TYPESAFE_BASE_URL` (default `https://api.typesafe.ai`), `TYPESAFE_DEFAULT_MODEL` (default `jev-latest`), `TYPESAFE_LOG_LEVEL` |
| Default timeout | 10 s per HTTP operation |
| Endpoint | `POST /v1/systemone` with body `{state, model, questions}` |

### Question types

| Type | Construct | Criteria | Answer object | Answer fields |
| --- | --- | --- | --- | --- |
| **Noul** (yes/no) | `Noul(instructions=..., criteria={"true": ..., "false": ...})` | optional descriptions of the yes and no outcomes | `NoulAnswer` | `noul: float` (probability of yes); **no confidence field** |
| **Choice** | `Choice(instructions=..., criteria={"label": "description" \| None, ...})` | label → description (text, JSON object or array) | `ChoiceAnswer` | `choice: str`, `confidence: float`, `probabilities: dict[str, float]` |
| **Score** | `Score(instructions=..., criteria=["level 0", "level 1", ...])` | ordered level descriptions, starting at 0 | `ScoreAnswer` | `score: float` (probability-weighted expected level), `confidence: float`, `legend: dict[int, ...]`, `probabilities: dict[int, float]` |

- `instructions` and every criteria value can be **structured JSON**, not only strings. Lifeform uses structured option descriptions for actions (see [07](07-jev-nervous-system.md)).
- A `SystemOneResponse` exposes `.answers`, `.choices`, `.scores`, `.nouls`, `.model` (the concrete version that answered) and `.usage.input_tokens` / `.usage.output_tokens`.
- Answer types the SDK version doesn't recognize are dropped with a warning rather than failing the response.

### Errors and retries

| Exception | Meaning | Lifeform response |
| --- | --- | --- |
| `TypeSafeRateLimitError` (429) | Over requests/min or tokens/s | Rate governor backs off (AIMD), and the call is retried |
| `TypeSafeAPITimeoutError`, `TypeSafeAPIConnectionError` | Network or timeout | Retry; after the retry budget is spent, the tick pauses (see 1.7 J12) |
| `TypeSafeInternalServerError` (5xx) | Server side | Retry |
| `TypeSafeBadRequestError`, `TypeSafeUnprocessableEntityError` | Our request is malformed | Fail fast: a bug in the state encoder or question panel |
| `TypeSafeAuthenticationError`, `TypeSafePermissionDeniedError` | Key problem | Abort the run before tick 0 (a preflight check) |

Default `RetryPolicy`: `max_retries=2`, `backoff_initial=0.5 s`, `backoff_max=5 s`, jitter 0.25, retried statuses `{408, 429, 5xx}`, honors `Retry-After`, total budget 30 s per call.

### Minimal call shape (reference only)

```python
async with AsyncTypeSafeClient(model="jev-1.13.0") as client:
    response = await client.system_one(state=mind_state, questions=question_panel)
    action = response.choices["action"]
```

---

## 1.3 Model facts

| Fact | Value | Source |
| --- | --- | --- |
| Current version | `jev-1.13.0` (aliases `jev-latest` and `jev-preview` both point to it) | TypeSafe Models page |
| Architecture | Non-autoregressive decision model, trained with RL for calibrated decisions ("RLCD") | flaviocopes.com deep dive |
| Input price | **$0.042 per million input tokens**; output tokens are free | Models page |
| Context | 64k tokens per request; the state plus the longest single question must fit in 32k | Models page |
| Rate limits | **1,200 requests/min** and **250,000 tokens/s** per key, "adjusting dynamically" and may change without notice | Models page |
| Latency | 70–500 ms end to end, mostly around 100 ms (*vendor-reported*); a drone project measured 0.11–0.12 s median and 0.164 s p90 | flaviocopes.com; jev-drone |
| Choice size | Up to 255 options (a third-party gateway caps it at 64) | dev.to guide; befailproof |
| Score size | 2–10 levels | flaviocopes.com |
| Input modality | Text only; English is best | Models page |
| Weights | Same weights for every account; customization happens only through state, instructions and criteria | Models page |
| Output guarantee | Answers always match the declared type (0% type errors) | TypeSafe blog |

---

## 1.4 Confidence semantics

- For a **Choice** with $n$ options and top probability $p_{max}$: $\text{confidence} = \dfrac{n \cdot p_{max} - 1}{n - 1}$. This is 0 for a flat distribution and 1 when one option has all the probability.
- For a **Score**, confidence measures how concentrated the probability is across levels.
- A **Noul** has no confidence field. Where Lifeform needs one, it uses $c = |2p - 1|$.
- Confidence is calibrated **in aggregate**: higher confidence really does mean higher accuracy. TypeSafe suggests three bands: **> 0.9** act, **0.5–0.9** act cautiously, **< 0.5** decline or escalate.
- The full `probabilities` distribution is always available. Lifeform samples actions from it (see [07 §7.6](07-jev-nervous-system.md)).

**Consequence for Lifeform:** confidence is a real, calibrated quantity, so we can give it a biological role: **decisiveness and hesitation**. The reference design's "confidence controls cognition" idea survives as "confidence modulates how an action is executed". The LLM escalation step is removed.

---

## 1.5 Known weaknesses (jev-1.13 "jaggedness") and how Lifeform designs around them

| Weakness (from TypeSafe docs) | What it would break here | Lifeform design response |
| --- | --- | --- |
| **Cannot count or do arithmetic**; numbers are not reliable quantities | "Energy 0.31" or "distance 4.2" would be read as text | **No raw numbers in state.** Every quantity passes through a `Quantizer` that turns it into words ("very near", "starving", "twice your size"). Code does all comparisons |
| **Dates and time comparisons are unreliable** | "Seen 37 ticks ago" | Time is also quantized into words: "just now", "earlier today", "yesterday", "days ago" |
| **Reads literally**; negations and implied conditions are taken at face value | "Don't approach unless safe" | Positive, atomic wording; boundary cases go in the criteria; option descriptions state their consequence plainly |
| **Irrelevant context lowers accuracy** | Dumping the whole 7×7 grid or every percept | A `SalienceRanker` keeps the state to about 600–900 tokens: top 6 entities, top 3 smells, top 3 sounds, top 4 memories |
| **The state has to contain the answer** (jev-drone lesson) | Jev can't infer "can I outrun it?" | Code precomputes relational facts: "it is faster than you", "deep water lies between you", "it has not noticed you" |
| **Indirection** (a property of a property) | "The animal that attacked your sibling" | Facts are pointed and direct: "P2 attacked your kin yesterday" |
| **No cross-question consistency** ($P(A) + P(\neg A) \ne 1$ across questions) | `threat` and `action` might disagree | Each answer is treated as an independent signal with its own role. There is no hard coupling logic between them |
| **Adversarial state can move answers** | Not a risk here: state is generated entirely by our code, so there is no untrusted text | Nothing needed; noted for completeness |
| **Contradictory instructions and criteria** | Muddy choices | A single wording source (`QuestionPanel`), reviewed in the Question Lab |
| **Unpinned models drift** | Thresholds tuned on 1.13 may shift silently | Pin `jev-1.13.0`, record `response.model` in every decision, and re-run the Question Lab when the version changes |

---

## 1.6 Prior art: Jev inside control loops

| Project | How it used Jev | Lesson for Lifeform |
| --- | --- | --- |
| **jev-drone** (MuJoCo quadrotor) | About 2.5 Hz tactical decisions. The scene is encoded symbolically (5 range sectors, obstruction height, target bearing). Three questions per call: `maneuver` (Choice), `risk` (Score), `target_truly_lost` (Noul). A 50 Hz code reflex layer keeps a veto | **Symbolic encoding works; raw values don't.** Adding a single missing fact (obstruction top edge) moved confidence to 0.93. The Choice/Score/Noul trio per call is the same shape as our Mind Panel |
| **jev-realtime-sdk** | An inner tick owned by code and a decision tick owned by Jev. Continuous state is bucketed into words (`far/mid/near`). Verbs are pre-filtered for safety, each decision has a default verb, and a circuit breaker covers consecutive failures | **Bucket everything; pre-filter the verbs (our affordances); log every decision's fate.** Lifeform is turn-based, so it has no staleness problem. That is simpler than their real-time case |
| **Game demos** (Minecraft, Subway Surfers, driving) | A live text description of game state, with Jev choosing from an allowed action menu | **Situational judgment over a menu of grounded options is Jev's sweet spot.** About 150k tokens for 2 minutes of Minecraft, roughly one cent |
| **TypeSafe "Function Calling" and "Skill Suggestion" cookbooks** | A Choice over typed candidates, including a 182-item catalog narrowed in two requests | Our action Choice over ≤ 32 affordances is well within tested territory |

---

## 1.7 Design rules for Lifeform (derived from the above)

| # | Rule |
| --- | --- |
| **J1** | **One Jev call per living organism per tick, and no more.** All of that organism's questions (action, effort, threat, signal, focus) ride in that one call (TypeSafe's "speculative fan-out"). |
| **J2** | **Words, not numbers.** The state never contains raw floats, coordinates or counts. Quantizers turn values into graded words. |
| **J3** | **The state contains the answer.** Code precomputes every relational fact a sensible animal would "just know": relative size, relative speed, whether it has been noticed, whether a path is blocked, and how long ago something happened. |
| **J4** | **Small, salient state.** The target is 600–900 tokens (hard cap 1,500), chosen by a salience ranker. |
| **J5** | **Grounded, legal options.** The action Choice is over *affordances* that code built from what is actually possible right now (for example `flee_from_P1`, `graze_here`, `court_P3`). Illegal options never appear, so Jev can't choose them. |
| **J6** | **Positive, literal, atomic wording**, with explicit "none" options where a question needs one (`silent`, `nothing_in_particular`). |
| **J7** | **Pin the model** (`jev-1.13.0`), log `response.model` and token usage, and re-run the Question Lab on any version change. |
| **J8** | **Use the whole distribution.** Actions are *sampled* from Jev's probabilities, sharpened by each organism's heritable decisiveness. Confidence modulates how the action is executed. |
| **J9** | **Throughput, not latency, is the limit.** One global `RateGovernor` serves every world running in parallel. |
| **J10** | **Record everything.** Every call's state, options, answers, model version, tokens and latency are written to the decision tape. Replays never call Jev again. |
| **J11** | **Independent answers stay independent.** No logic assumes the action and threat answers agree. |
| **J12** | **No code-chosen actions, ever.** The simulation is turn-based, so the engine waits for every decision before resolving the tick. A failed call is retried; persistent failure *pauses* the run at a checkpoint. It never substitutes a code-chosen action. The only exception is the `stalled` outcome (the organism does nothing). It is labeled and counted, and it should stay near zero. |

---

## 1.8 Throughput and cost model

Let $W$ be the number of worlds, $T$ the ticks per world, $\bar N$ the mean living organisms, and $\bar k$ the mean input tokens per call.

$$\text{calls} = W \cdot T \cdot \bar N \qquad \text{wall time} \ge \frac{\text{calls}}{1200}\ \text{min} \qquad \text{cost} = \text{calls} \cdot \bar k \cdot \frac{\$0.042}{10^6}$$

The tokens-per-second limit is not binding: at 20 requests/s × 1,300 tokens = 26k tokens/s, which is about 10% of the 250k tokens/s limit.

| Profile | Worlds | Ticks | Mean organisms | Calls | Wall time at 1,200 RPM | Cost at ~1,300 tokens per call |
| --- | --- | --- | --- | --- | --- | --- |
| `smoke` | 1 | 60 | 30 | 1.8k | ~2 min | ~$0.10 |
| `preview` | 12 | 300 | 50 | 180k | ~2.5 h | ~$10 |
| `standard` | 12 | 1,500–3,000 (20,000 world-ticks in total) | 80 | 1.6M | ~22 h | ~$87 |
| `deep-evolution` (one world) | 1 | 6,000 | 100 | 600k | ~8.3 h | ~$33 |

**Levers**, in the order we would pull them:

1. Carrying-capacity calibration keeps $\bar N$ inside the target band (see [05 §5.16](05-ecology-rules.md)).
2. Smaller maps for experiment worlds.
3. Fewer ticks per day. The calendar is configurable; see [03 §3.2](03-world-model.md).
4. A higher-tier key. Enterprise customers can request higher limits.
5. The optional `economy` mode (**off by default**). It lets Jev commit to multi-tick actions such as sleeping until disturbed. It is a labeled deviation from J1 and is recorded in the run manifest.

`lifeform estimate <preset>` prints this table for any configuration before a run starts, and `--budget-usd` / `--max-calls` stop a run cleanly at a checkpoint.

---

## 1.9 Reuse from the user's existing code

`projects/immune/immune-ai/src/immune/sensing/jev.py` already has a working adapter. Its patterns carry over directly:

- a lazily created `AsyncTypeSafeClient` with a tight `RetryPolicy` and an explicit `aclose()`;
- a clean map from SDK answer types to a domain `Signal`, which becomes a domain `RawDecision` here;
- SDK exceptions wrapped into a domain exception (`SensorUnavailable`, which becomes `BrainUnavailable`);
- the `live` pytest marker for tests that need `TYPESAFE_API_KEY`.

The same `typesafe-sdk>=0.7.1,<0.8` pin and the ruff/mypy-strict configuration style are reused. See [02 §2.11](02-architecture.md).

---

## 1.10 Sources

- [Introducing System One Models & Jev — TypeSafe blog](https://typesafe.ai/blog/introducing-system-one-models-and-jev)
- [TypeSafe docs index (llms.txt)](https://docs.typesafe.ai/llms.txt)
- [Models: versions, limits, pricing](https://docs.typesafe.ai/models.md)
- [State](https://docs.typesafe.ai/concepts/state.md) · [Choice](https://docs.typesafe.ai/primitives/choice.md) · [Advanced structure](https://docs.typesafe.ai/primitives/advanced.md) · [Confidence](https://docs.typesafe.ai/confidence.md)
- [Speculative fan-out](https://docs.typesafe.ai/patterns/fan-out.md)
- [Jev 1.13 jaggedness (known limitations)](https://docs.typesafe.ai/model-jaggedness/jev-1.13.md)
- [How to Use Jev: a practical guide (DEV Community)](https://dev.to/valyuai/how-to-use-jev-a-practical-guide-to-typesafes-system-one-model-g5e)
- [A deep dive into Jev (flaviocopes.com)](https://flaviocopes.com/jev/)
- [jev-drone: MuJoCo drone with Jev in the loop](https://github.com/RomanSlack/jev-drone)
- [jev-realtime-sdk: code-owned inner tick, Jev-owned decision tick](https://github.com/chy4pro/jev-realtime-sdk)
- [Jev real-time game demos reviewed (MindStudio)](https://www.mindstudio.ai/blog/jev-real-time-game-demos)
- [Jev: TypeSafe's System One model (DataCamp)](https://www.datacamp.com/blog/system-one-models-jev)
- [TypeSafe Python SDK on PyPI](https://pypi.org/project/typesafe-sdk/)
