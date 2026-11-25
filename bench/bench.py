"""Benchmarks: python bench/bench.py  -> prints tables, writes bench/results.json

1. Scheduler: greedy O(n log n) vs quickselect O(n) wall time, n = 10^3..10^6
2. Scheduler savings on the sample day: run now vs flexible start vs optimal
3. Router: knapsack DP time vs number of requests
"""
import json
import pathlib
import random
import statistics
import time

from effitrap import (
    Model, flexible_start, greedy_schedule, linear_schedule, route_budgeted,
    run_now, schedule_cost,
)
from effitrap.carbon import SAMPLE_DAY

OUT = {}


def timed(fn, reps=3):
    ts = []
    for _ in range(reps):
        t = time.perf_counter()
        fn()
        ts.append(time.perf_counter() - t)
    return statistics.median(ts)


rng = random.Random(42)
print("1) Scheduler scaling (median of 3 runs)")
print(f"{'n':>9} {'greedy sort (ms)':>17} {'quickselect (ms)':>17}")
rows = []
for n in (1_000, 10_000, 100_000, 1_000_000):
    c = [rng.uniform(20, 400) for _ in range(n)]
    e = n * 0.25
    tg = timed(lambda: greedy_schedule(c, e, 1.0))
    tl = timed(lambda: linear_schedule(c, e, 1.0))
    rows.append({"n": n, "greedy_ms": tg * 1e3, "linear_ms": tl * 1e3})
    print(f"{n:>9,} {tg * 1e3:17.1f} {tl * 1e3:17.1f}")
OUT["scaling"] = rows

print("\n2) Sample day, 4-hour job (illustrative curve)")
plans = {"run_now": run_now, "flexible_start": flexible_start, "optimal": linear_schedule}
base = schedule_cost(SAMPLE_DAY, run_now(SAMPLE_DAY, 4, 1))
sav = {}
for name, f in plans.items():
    cost = schedule_cost(SAMPLE_DAY, f(SAMPLE_DAY, 4, 1))
    sav[name] = {"emissions": cost, "saving_pct": (1 - cost / base) * 100}
    print(f"   {name:<15} {cost:7.0f}  ({sav[name]['saving_pct']:.0f}% less than running now)")
OUT["sample_day"] = sav

print("\n3) Budgeted router DP (4 models per request, budget = 2 Wh per request, 0.1 Wh units)")
models = [Model("a", 0.1, 0.55), Model("b", 0.3, 0.7), Model("c", 4.0, 0.85), Model("d", 8.0, 0.95)]
rrows = []
for n in (10, 50, 100, 200):
    t = timed(lambda: route_budgeted([models] * n, 2.0 * n), reps=1)
    rrows.append({"requests": n, "ms": t * 1e3})
    print(f"   {n:>4} requests: {t * 1e3:8.1f} ms")
OUT["router"] = rrows

path = pathlib.Path(__file__).with_name("results.json")
path.write_text(json.dumps(OUT, indent=2))
print(f"\nwrote {path}")
