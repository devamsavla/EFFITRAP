# EFFITRAP

AI keeps getting cheaper per answer, but we use so much more of it that its total electricity keeps rising. Here are four simple fixes. Each one: look, press, see the saving.

**Links:** [Slides](https://claude.ai/artifact/BkwQSYMXYQsRBkg9JehDGi) · [Playground](https://claude.ai/artifact/QoYE25MmjTCHMezgWodZzL) · [Paper (PDF)](docs/efficiency-trap-paper.pdf)

*NYU CS-GY 6033G Design and Analysis of Algorithms I · final project.*

**Algorithms for escaping AI's efficiency trap.**

> Every green-AI tool makes each job cheaper. That's exactly the trap: cheaper jobs → more jobs → a bigger total. **effitrap also caps the total.**
AI got 33× cheaper per answer in a year and still used more electricity. This package implements the four moves out, each as a real algorithm with tests and benchmarks.

*CS-GY 6033G Design and Analysis of Algorithms I · NYU · Student ID N18349850*

| Move | Module | Algorithm | Complexity |
|---|---|---|---|
| 🩺 Do less | `router` | Budgeted model routing = multiple-choice knapsack, dynamic programming | O(n·m·B) |
| 🚌 Share | `batching` | Amortised cost F/b + v; best batch by binary search under memory + latency limits | O(log b) |
| 🧑‍💼 Share | `speculative` | Speculative decoding: closed form (geometric series) + Monte Carlo check | O(γ) |
| ☀️ Time it | `schedule` | Carbon-aware scheduling: greedy (sort) and quickselect; baselines run-now and flexible-start (sliding window) | O(n log n) / O(n) expected |
| 🎯 Cap it | `budget`, `experiment` | Fixed energy budget; multiple-choice knapsack with a defer option; one-year experiment vs per-job efficiency | O(n·m·B) |
| 👀 Show it | `identity`, `units` | E = Σ N·w·ε decomposition, rebound bound, Wh → phone charges | O(k) |


**Doesn't a rate limit already do this?** A rate limit is a bouncer: same energy cap, first come first served. At the IEA's growth pace, after a year it answers 61% of requests; the knapsack, with the *same energy*, answers 100% (95% at full quality). At 30× growth: 38% vs 100%. Run `effitrap experiment` to see it.


## What is it for? (in one breath)

effitrap does **not** change the AI model. It sits **between your app and the AI**, like a smart door, and answers three questions before each call:

| Question | effitrap's answer |
|---|---|
| 🐭 Which brain? | the smallest model that's good enough for this request |
| ☀️ Now or later? | if it isn't urgent, wait for cleaner electricity |
| 🎒 How much is left? | a running energy budget; when it's tight, right-size instead of refusing people |

### Use it in 3 lines

```bash
pip install effitrap.zip        # no other dependencies
```

```python
from effitrap import Gate
gate = Gate(budget_wh=5000)                     # this week's AI energy
choice = gate.pick("Summarise this email")      # -> tiny model, 0.1 Wh
answer = call_my_ai(choice.model, prompt)       # your existing code, unchanged
```

Or from the terminal: `effitrap pick "Prove this theorem"` · `effitrap run --gb -- python train.py` · `effitrap budget status`.

### Only use Claude?

Claude is already a family, so you still never switch models by hand: `Gate(models=CLAUDE_FAMILY)` sends easy questions to Haiku, medium ones to Sonnet and hard ones to Opus. Questions that can wait go out later as one Message Batch at the cleanest hour (Anthropic bills batches at 50%). Full example: `examples/claude_only.py`. Energy per Claude answer isn't published, so the defaults are IEA-based stand-ins.

### Where the pollution forecast comes from

`--gb`: Great Britain's free half-hourly forecast (checked live on 2026-11-24; a recording is in `tests/data/`). `--zone DE`: any Electricity Maps zone (needs a token with forecast access). `--csv`: your own numbers. While waiting, `effitrap run` re-checks a live forecast every 30 min (`--replan`), keeps the last plan if a download fails, starts at once if there is no forecast at all, and never misses the deadline. With forecasts off by up to ±30% each hour, waiting still saved 54% on average across 300 simulated days.

**Honest scope:** batching and speculative decoding happen inside serving engines such as vLLM; effitrap computes the best settings for them (`effitrap batch`, `effitrap spec`) but doesn't replace them. Difficulty is estimated with a simple heuristic; plug in a trained router (e.g. RouteLLM) for production.

## Why would you use this? 🤔

Every AI job uses electricity. effitrap gives you three things you can do **today**, without new hardware:

| You are… | You type… | You get… |
|---|---|---|
| 🧑‍🎓 a student or researcher training a model | `effitrap run --hours 4 --within 24 --gb -- python train.py` | Your job waits for the cleanest hours on the grid, then starts by itself. Same results, less carbon (77% on the sample day). |
| 🏗️ building an app on top of AI models | `route_threshold(...)` / `route_budgeted(...)` in your code | Easy questions go to small models and hard ones to big models. On the demo questions: 12.8 Wh instead of 48 Wh (−73%), within an energy budget you set. |
| ⚙️ running your own model server | `effitrap batch --memory 80 --weights 26 --kv 0.8 --sla 50` | The biggest batch that fits your memory and latency limit, and how much paging memory would gain you. |
| 🎓 teaching, writing or arguing about AI energy | `effitrap day`, `effitrap trap` | Honest numbers in phone charges, and the Jevons maths in one line. |

**Scope, honestly:** effitrap plans *when* and *how* to compute. It doesn't measure your hardware's power draw, and the router's quality scores are yours to supply. Run it beside your existing tools, not instead of them.

## Install

```bash
pip install -e .            # library + CLI, no dependencies
pip install -e ".[api]"     # + HTTP API (FastAPI)
pip install -e ".[dev]"     # + tests (pytest, scipy oracle, httpx)
```

## Use it

```bash
effitrap day                        # what a day of AI costs (spoiler: the videos)
effitrap schedule                   # when to run a 4-hour job (illustrative sample day)
effitrap schedule --csv grid.csv    # with your own carbon-intensity data
effitrap schedule --gb              # with Great Britain's live forecast (api.carbonintensity.org.uk)
effitrap route --budget 10          # pick models for 6 requests within 10 Wh
effitrap batch --waste 0.7          # best batch size before/after PagedAttention-style paging
effitrap spec --alpha 0.8 --c 0.05  # best draft length for speculative decoding
effitrap trap --total 1.5 --per-task 0.1   # how much demand must have grown (Jevons bound)
effitrap run --hours 4 --within 24 --gb -- python train.py   # wait for clean power, then run
effitrap budget set 5000            # cap this week's AI energy (Wh)
effitrap budget spend 120 --name train
effitrap experiment                 # each-job-cheaper vs capped total, one year
```

## The experiment

Same requests, same efficiency gains (×10/yr), demand ×15/yr (both implied by IEA 2026). Today's tools (cheapest adequate model per request) end the year at **1.5×** the energy. effitrap's cap holds at **≤1.0×**, answering 100% of requests, 95% at full quality. At ×60 demand the cap still holds but must defer 28%, making the trade-off visible. Question mix and model quality are illustrative; energies per answer are IEA lab values.


```python
from effitrap import linear_schedule, schedule_cost
c = [300, 290, 120, 70, 65, 90, 250]     # g CO2/kWh per hour
x = linear_schedule(c, energy=3, cap=1)   # -> [0, 0, 0, 1, 1, 1, 0]
```

HTTP API: `uvicorn effitrap.api:app` → `POST /schedule`, `POST /route`, `GET /day`, `GET /health`.

## Proof that greedy is optimal (scheduling)

Minimise Σ c[t]·x[t] subject to Σ x[t] = E and 0 ≤ x[t] ≤ P.
If some energy sits in a dirtier slot j while a cleaner slot i (c[i] < c[j]) has room, move δ = min(P − x[i], x[j]) from j to i: the cost changes by δ(c[i] − c[j]) < 0. So an optimal schedule never leaves a cleaner slot unfilled while using a dirtier one, which is exactly the greedy schedule. Every slot has the same capacity, so the job uses the ⌈E/P⌉ cleanest slots: quickselect finds the threshold in expected O(n).

## Tests: 47 checks, run on 904 random cases

```bash
pytest -q
```

- Scheduler: greedy == quickselect on 300 random instances (with ties); matches a **linear-programming oracle** (scipy HiGHS) on 100; the exchange invariant holds; baselines never beat optimal.
- Router: DP == **brute force** over every combination on 120 random instances; budget never exceeded.
- Batching: binary search == linear scan over 20 configurations; costs fall with diminishing returns.
- Speculative decoding: closed form == Monte Carlo (200k trials) within 1%.
- CLI and HTTP API tests, including `effitrap run` actually launching a command.

The test suite caught one real bug: when a job needed every slot, the partial slot went to the wrong hour. Fixed in `schedule.py`. 🐛→✅

## Benchmarks (`python bench/bench.py`)

| n slots | greedy sort | quickselect |
|---:|---:|---:|
| 1,000 | 0.1 ms | 0.3 ms |
| 10,000 | 1.6 ms | 1.2 ms |
| 100,000 | 26.9 ms | 19.3 ms |
| 1,000,000 | 270 ms | 172 ms |

Asymptotics win at scale (1.6× at a million slots); at small n, sorting's low constant factor wins. Your numbers will vary by machine.

Sample day, 4-hour job: running now 1,185 units → optimal 269 (−77%).

## Where the numbers come from

- Per-task energy: IEA, *Energy and AI* (2025), lab tests, GPU only: text 0.3 Wh, image 1.7 Wh, 6 s video 115 Wh; phone charge ~15 Wh, laptop ~60 Wh.
- "Day of AI" mix (15 texts, 10 images, 3 videos): MIT Technology Review (2025).
- Batching, paging, speculative decoding: IEA (2025); Kwon et al. (SOSP 2023); Leviathan et al. (ICML 2023).
- Sample carbon curve: **illustrative**, shaped like MIT Technology Review's California example (<70 g/kWh afternoon, >300 at night).
- Router quality scores and batching constants: **illustrative defaults**. Pass your own.

## Licence
MIT
