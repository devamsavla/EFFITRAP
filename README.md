# EFFITRAP 🪤

AI keeps getting cheaper per answer, but we use so much more of it that its total electricity keeps rising. Here are four simple fixes. Each one: look, press, see the saving.

**📽️ [Slides (live)](https://claude.ai/artifact/BkwQSYMXYQsRBkg9JehDGi)** · **🕹️ [Playground](https://claude.ai/artifact/QoYE25MmjTCHMezgWodZzL)** · **📄 [Paper (PDF)](docs/efficiency-trap-paper.pdf)** · **🖼️ [Slides (PowerPoint)](docs/The-Efficiency-Trap-slides.pptx)**

*NYU CS-GY 6033G Design and Analysis of Algorithms I · final project · Student ID N18349850*

---

## The idea in 30 seconds

- Google made each AI answer **33× cheaper** in one year. Electricity for AI data centres still went **+50%** (IEA, 2026). Cheaper answers → many more answers → a bigger total. That's the **Jevons paradox**.
- So instead of only making each answer cheaper, effitrap answers an algorithms question: **how do we run AI under a fixed energy budget, at the cleanest hours, and still answer everyone well?**
- It splits into two problems, each solved by a classic algorithm and checked against a slower, trusted method:

| Question | Everyday idea | Algorithm | Checked against |
|---|---|---|---|
| ☀️ **WHEN** should a job run? | take the cleanest hours | greedy (proved optimal), quickselect, sliding window | a linear-programming solver |
| 🎒 **WHICH** model, within budget? | pack a backpack: most value, limited space | knapsack, dynamic programming | trying every combination |
| 🚌 Bonus: how many per trip? | split the taxi fare | amortised cost, binary search | checking every size |
| 🧑‍💼 Bonus: the intern trick | marking is faster than writing | speculative decoding, geometric series | 200,000 simulated runs |

---

## Live demo (2 minutes) 🎬

```bash
pip install .            # from this folder; the core has no dependencies (Python 3.9+)
```

### 1. What does a day of AI cost?
```
$ effitrap day
🗓️  A day of AI: 15 texts, 10 images, 3 videos
   text        4.5 Wh  █
   image      17.0 Wh  █
   video     345.0 Wh  ████████████████████████████
   total     366.5 Wh = 0.37 kWh
   ≈ 24 phone charges 📱  ≈ 6.1 laptop charges 💻
   🎬 Verdict: the videos did it. It's always the videos.
```

### 2. ☀️ WHEN: wait for the sun
```
$ effitrap schedule
🏃 run now                  1185.0 g CO₂  (   0% less)  hours [0, 1, 2, 3]
⏰ flexible start            269.0 g CO₂  (  77% less)  hours [12, 13, 14, 15]
🧠 greedy (optimal)          269.0 g CO₂  (  77% less)  hours [12, 13, 14, 15]
☀️  The sun says you're welcome.
```
With live data for Great Britain (free, no key), plan a 4-hour job and launch it at the cleanest time:
```
$ effitrap run --hours 4 --within 24 --gb -- python train.py
```
It re-checks the forecast every 30 minutes, keeps its plan if a download fails, and never misses the deadline. Add `--dry-run` to see the plan without starting anything.

### 3. 🎒 WHICH: the backpack trick
```
$ effitrap pick "Translate good morning into Hindi" --budget 5000
🧠 difficulty 0.21 → use tiny (0.1 Wh) · 4999.9 Wh left
$ effitrap pick "Prove this theorem about prime numbers"
🧠 difficulty 0.99 → use big (8 Wh) · 4991.9 Wh left
$ effitrap budget status
🔋 ░░░░░░░░░░░░░░░░░░░░ 0% used · 8.1 of 5000 Wh · 4991.9 Wh left
```
```
$ effitrap route
🎒 Budgeted router (knapsack DP), budget 10.0 Wh -> quality 4.50:
   small (9B), small (9B), medium (70B), small (9B), small (9B), medium (70B)
   uses 9.2 Wh.
```

### 4. Does it beat a rate limit? (same energy, one simulated year)
```
$ effitrap experiment
month   each job cheaper  effitrap cap   answered  full quality  rate limit answers
    0              1.00x         0.93x       100%           99%                100%
   12              1.50x         0.89x       100%           95%                 61%
🚪 A rate limit with the SAME energy answers 61%. Bouncer vs knapsack.
```
*(Rows for months 3–9 omitted here.)*

### 5. 🚌 The bus and 🧑‍💼 the intern (for the companies running the AI)
```
$ effitrap batch
🚌 before (wasteful memory)   max fit  20, best batch  20, energy/request  10.00 J (vs 105 J alone)
🚌 after PagedAttention       max fit  64, best batch  60, energy/request   6.67 J (vs 105 J alone)
$ effitrap spec
🧑‍💼 alpha=0.8, draft cost ratio c=0.05: best draft length gamma=8
   tokens per big-model call: formula 4.329, simulation 4.312
   expected speed-up ≈ 3.09x. The intern is worth it.
```

### 6. Prove it's right
```
$ pip install pytest scipy && pytest
906 passed in ~9 s
```

---

## Use it in your own code (one line)

effitrap never touches the AI model. It sits between your app and **any** AI and decides **which model** and **when**.

```python
from effitrap import Gate, CLAUDE_FAMILY

gate = Gate(budget_wh=5000, models=CLAUDE_FAMILY)   # this week's AI energy
choice = gate.pick(prompt)                           # → claude-haiku / sonnet / opus, or None = wait
if choice.model:
    reply = client.messages.create(model=choice.model, max_tokens=1024,
                                   messages=[{"role": "user", "content": prompt}])
```
- Any provider: pass your own `Model("name", wh_per_answer, quality)` list.
- A group of requests: `gate.pick_many(prompts)` solves the exact knapsack for the whole group.
- Full Claude example (batching deferrable work at the cleanest hour): [`examples/claude_only.py`](examples/claude_only.py).
- Web API: `pip install .[api]` then `uvicorn effitrap.api:app` (`/schedule`, `/route`, `/day`, `/health`).

---

## What's inside

| File | Answers the question | Algorithm |
|---|---|---|
| `effitrap/gate.py` | “Which brain, now or later, budget left?” (start here) | knapsack DP for groups |
| `effitrap/schedule.py` | “Which hours should my job run in?” | greedy · quickselect O(n) · sliding window O(n) |
| `effitrap/router.py`, `budget.py` | “Best answers without going over budget?” | multiple-choice knapsack, O(n·m·B) |
| `effitrap/batching.py` | “How many requests per trip?” | amortised cost · binary search O(log b) |
| `effitrap/speculative.py` | “How many of the intern's words survive?” | geometric series + Monte Carlo check |
| `effitrap/carbon.py` | “Where does the pollution forecast come from?” | GB API · Electricity Maps · CSV |
| `effitrap/experiment.py` | “Does it beat a rate limit?” | one-year simulation |
| `bench/bench.py` | “How fast is it?” | sort vs quickselect at 10³–10⁶ hours |

## How the tests work

Every test solves a problem **two ways** and compares: my fast algorithm against a slow, trusted method, on seeded random inputs anyone can replay.

| Check | Random data | Compared against | Cases |
|---|---|---|---|
| ☀️ cleanest hours | days of 1–40 hours, pollution 20–400 (ties on purpose) | SciPy linear programming + a second algorithm | 600 |
| 🎒 backpack trick | 1–5 requests × 1–4 models, random budgets | every combination (brute force) | 180 |
| 🚪 vs rate limit | a year at 15×, 30×, 60×, 120× growth | first come, first served, same energy | 8 |
| 🌦️ forecasts | the real GB forecast (24 Nov 2026) + 300 days with ±30% error | the true values; deadline never missed | 59 |
| 🚌 bus size | memory-waste × latency settings | checking every size | 20 |
| 🧑‍💼 intern formula | 4 settings | 200,000 simulated runs | 4 |
| 🧮 slide examples + 🛠️ the rest | greedy 7 vs best 10; the hand-worked table; every command, API, Claude example | known answers | 35 |

The tests also caught one real bug during development: when a job needed every hour, the fast scheduler picked hours in the wrong order.

## Honest limits

- It plans with **estimates**: AI companies don't publish energy per answer, so defaults come from IEA lab measurements. Plug in your own.
- Difficulty is guessed by a simple rule; a trained router (e.g. RouteLLM) can replace it.
- Live forecasts are free only for Great Britain; elsewhere use Electricity Maps (paid key) or your own numbers.
- The one-year experiment uses IEA growth rates but an illustrative question mix.
- An algorithm can spend a budget well. **Choosing the budget is a human decision.**

## Where the numbers come from

IEA *Energy and AI* (2025) and *Key Questions on Energy and AI* (2026) · Google, Elsworth et al. (2025) · MIT Technology Review (2025) · National Grid carbon-intensity API · full list in the [paper](docs/efficiency-trap-paper.pdf).

## Licence

MIT. See [LICENSE](LICENSE).
