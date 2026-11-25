"""effitrap command line. Try:  effitrap --help

    effitrap day                         what a day of AI costs, in phone charges
    effitrap schedule --energy 4         when to run a 4-slot job (sample day)
    effitrap schedule --csv grid.csv     ...with your own intensity data
    effitrap schedule --gb               ...with Great Britain's live forecast
    effitrap route --budget 10           pick models for 6 requests under 10 Wh
    effitrap batch --waste 0.7           best batch size, before/after PagedAttention
    effitrap spec --alpha 0.8 --c 0.05   speculative decoding: best draft length
    effitrap trap --total 1.5 --per-task 0.1   how much demand grew (the Jevons bound)
    effitrap run --hours 4 --within 24 --gb -- python train.py
                                         wait for the cleanest 4 hours, then start your job
    effitrap budget set 5000             cap this week's AI energy at 5,000 Wh
    effitrap budget spend 120 --name train   charge a job (refused if over budget)
    effitrap budget status               how much is left
    effitrap pick "Summarise this email"  which AI brain to use (charges the budget)
    effitrap experiment                  each-job-cheaper vs capped total, over a year
"""
from __future__ import annotations

import argparse
import math
import subprocess
import sys
import time
from datetime import datetime, timedelta

from . import __version__
from .batching import BatchConfig, best_batch, cost_per_request, max_batch
from .carbon import SAMPLE_DAY, fetch_electricitymaps_forecast, fetch_gb_forecast, load_csv
from .identity import implied_demand_growth
from .router import IEA_MODELS, Model, route_budgeted, route_threshold
from .schedule import flexible_start, linear_schedule, run_now, schedule_cost
from .speculative import best_gamma, expected_tokens, simulate_tokens, speedup
from .units import day_of_ai


def _bar(v: float, vmax: float, width: int = 30) -> str:
    return "█" * max(1, round(v / vmax * width)) if vmax else ""


def cmd_day(a):
    d = day_of_ai(a.texts, a.images, a.videos)
    print(f"🗓️  A day of AI: {a.texts} texts, {a.images} images, {a.videos} videos")
    for k in ("text", "image", "video"):
        print(f"   {k:<6} {d[k + '_wh']:8.1f} Wh  {_bar(d[k + '_wh'], d['wh'])}")
    print(f"   total  {d['wh']:8.1f} Wh = {d['kwh']:.2f} kWh")
    print(f"   ≈ {d['phone_charges']:.0f} phone charges 📱  ≈ {d['laptop_charges']:.1f} laptop charges 💻")
    if d["video_wh"] > 0.5 * d["wh"]:
        print("   🎬 Verdict: the videos did it. It's always the videos.")


def cmd_schedule(a):
    if a.gb:
        c = fetch_gb_forecast(a.hours)
        unit = "half-hour"
    elif a.csv:
        c = load_csv(a.csv)
        unit = "slot"
    else:
        c = SAMPLE_DAY
        unit = "hour"
        print("ℹ️  Using an illustrative sample day (not real data). Try --csv or --gb.")
    plans = {
        "🏃 run now": run_now(c, a.energy, a.cap),
        "⏰ flexible start": flexible_start(c, a.energy, a.cap),
        "🧠 greedy (optimal)": linear_schedule(c, a.energy, a.cap),
    }
    base = schedule_cost(c, plans["🏃 run now"])
    for name, x in plans.items():
        cost = schedule_cost(c, x)
        saving = 0 if base == 0 else (1 - cost / base) * 100
        slots = [t for t, v in enumerate(x) if v > 0]
        print(f"{name:<22} {cost:10.1f} g CO₂  ({saving:4.0f}% less)  {unit}s {slots}")
    print("☀️  The sun says you're welcome." if c is SAMPLE_DAY else "🌍 Done.")


def cmd_route(a):
    required = [0.5, 0.5, 0.6, 0.7, 0.8, 0.9][: a.requests]
    picks = route_threshold(required, IEA_MODELS)
    total = sum(m.wh for m in picks if m)
    print("🩺 Threshold router (cheapest model that is good enough):")
    for need, m in zip(required, picks):
        print(f"   needs {need:.1f} -> {m.name if m else 'nobody 😬'}  ({m.wh if m else 0} Wh)")
    print(f"   total {total:.1f} Wh")
    options = [[Model(m.name, m.wh, m.quality) for m in IEA_MODELS] for _ in required]
    q, chosen = route_budgeted(options, a.budget)
    print(f"🎒 Budgeted router (knapsack DP), budget {a.budget} Wh -> quality {q:.2f}:")
    print("   " + ", ".join(m.name for m in chosen))
    print(f"   uses {sum(m.wh for m in chosen):.1f} Wh. (Quality scores are illustrative inputs.)")


def cmd_batch(a):
    for label, waste in (("before (wasteful memory)", a.waste), ("after PagedAttention", 0.04)):
        cfg = BatchConfig(fixed_j=a.fixed, marginal_j=a.marginal, memory_gb=a.memory,
                          weights_gb=a.weights, kv_gb=a.kv, waste=waste, sla_ms=a.sla)
        b = best_batch(cfg)
        print(f"🚌 {label:<26} max fit {max_batch(cfg):3d}, best batch {b:3d}, "
              f"energy/request {cost_per_request(max(b, 1), cfg):6.2f} J (vs {cost_per_request(1, cfg):.0f} J alone)")
    print("   (F, v, memory and latency numbers are illustrative defaults; pass your own via the API.)")


def cmd_spec(a):
    g = best_gamma(a.alpha, a.c)
    print(f"🧑‍💼 alpha={a.alpha}, draft cost ratio c={a.c}: best draft length gamma={g}")
    print(f"   tokens per big-model call: formula {expected_tokens(a.alpha, g):.3f}, "
          f"simulation {simulate_tokens(a.alpha, g, 50_000):.3f}")
    print(f"   expected speed-up ≈ {speedup(a.alpha, g, a.c):.2f}x. The intern is worth it.")


def cmd_trap(a):
    g = implied_demand_growth(a.total, a.per_task)
    print(f"🪤 Total energy x{a.total}, energy per task x{a.per_task} -> demand grew at least x{g:.0f}.")
    print("   Jevons, 1865: 'told you so.'")


def _intensities(a):
    """Return (intensities, slot length in hours, is_sample)."""
    if getattr(a, "gb", False):
        return fetch_gb_forecast(getattr(a, "within", 24)), 0.5, False
    if getattr(a, "zone", None):
        import os
        token = os.environ.get("ELECTRICITYMAPS_TOKEN")
        if not token:
            raise ValueError("set ELECTRICITYMAPS_TOKEN to use --zone")
        return fetch_electricitymaps_forecast(a.zone, token, int(getattr(a, "within", 24))), 1.0, False
    if getattr(a, "csv", None):
        return load_csv(a.csv), getattr(a, "slot_hours", 1.0), False
    return SAMPLE_DAY, 1.0, True


def best_start(c, need):
    """Index of the cleanest run of `need` consecutive slots (sliding window, O(n))."""
    plan = flexible_start(c, need, 1)
    return next(t for t, v in enumerate(plan) if v > 0)


def wait_and_replan(get_forecast, need, slots_left, slot_h, replan_slots, sleep=time.sleep, log=print):
    """Wait for the cleanest window, re-checking the forecast as we go.

    Forecasts change and can be wrong, so every `replan_slots` we fetch again and re-pick
    the window from what is left. If a fetch fails we keep the last plan; if there is no
    plan at all we start now. The deadline (`slots_left`) is never missed. Returns the
    number of slots waited."""
    waited = 0
    last = None
    while True:
        try:
            c = list(get_forecast())[:slots_left]
            if len(c) >= need:
                last = best_start(c, need)
        except Exception as e:
            log(f"⚠️  Forecast unavailable ({e}). " + ("Keeping the last plan." if last is not None else "Starting now to be safe."))
            if last is None:
                return waited
        if last is None or last <= 0 or slots_left <= need:
            return waited
        step = min(last, replan_slots)
        log(f"😴 Cleanest window starts in {last * slot_h:g} h. Re-checking the forecast in {step * slot_h:g} h.")
        sleep(step * slot_h * 3600)
        waited += step
        slots_left -= step
        last -= step


def cmd_run(a):
    try:
        c, slot_h, sample = _intensities(a)
    except Exception as e:
        print(f"⚠️  Could not get a forecast ({e}). Running now so your deadline is safe.")
        c, slot_h, sample = None, 1.0, False
    if c is not None:
        c = c[: max(1, int(a.within / slot_h))]
        need = max(1, math.ceil(a.hours / slot_h - 1e-9))
        if need > len(c):
            raise ValueError(f"job needs {a.hours} h but the window is only {len(c) * slot_h:g} h")
        start = best_start(c, need)
        saving = 1 - schedule_cost(c, flexible_start(c, need, 1)) / schedule_cost(c, run_now(c, need, 1))
        when = datetime.now() + timedelta(hours=start * slot_h)
        if sample:
            print("ℹ️  Sample day (illustrative). Use --gb (Great Britain, free), --zone (any country, "
                  "Electricity Maps key) or --csv for real data.")
        print(f"🔎 Cleanest {a.hours:g}-hour window in the next {a.within:g} h starts in {start * slot_h:g} h "
              f"(~{when:%a %H:%M}), {saving * 100:.0f}% less carbon than starting now.")
    if a.command and a.command[0] == "--":
        a.command = a.command[1:]
    if a.dry_run or not a.command:
        print("🧪 Dry run: nothing started." if a.command else "ℹ️  No command given; plan only.")
        return
    if c is not None and start > 0:
        live = a.gb or getattr(a, "zone", None)
        replan = max(1, int(a.replan / 60 / slot_h)) if live else 10 ** 9
        wait_and_replan(lambda: _intensities(a)[0] if live else c, need, len(c), slot_h, replan)
    print(f"🚀 Running: {' '.join(a.command)}")
    rc = subprocess.call(a.command)
    if rc != 0:
        raise ValueError(f"your command exited with code {rc}")


LEDGER = ".effitrap-budget.json"


def cmd_budget(a):
    import os
    from .budget import Ledger
    path = a.file
    if a.action == "set":
        Ledger(budget_wh=a.amount).save(path)
        print(f"🎯 Budget set: {a.amount:g} Wh for this period. Efficiency savings now buy quality, not growth.")
        return
    if not os.path.exists(path):
        raise ValueError("no budget yet: run `effitrap budget set <Wh>` first")
    led = Ledger.load(path)
    if a.action == "spend":
        led.charge(a.name, a.amount)
        led.save(path)
    pct = led.spent_wh / led.budget_wh * 100 if led.budget_wh else 0
    bar = "█" * round(pct / 5) + "░" * (20 - round(pct / 5))
    print(f"🔋 {bar} {pct:.0f}% used · {led.spent_wh:g} of {led.budget_wh:g} Wh · {led.left_wh:g} Wh left")
    if pct >= 80:
        print("⚠️  Running low: effitrap would now pick smaller models and defer flexible jobs.")


def cmd_experiment(a):
    from .experiment import run
    rows = run(demand_per_year=a.demand, efficiency_per_year=a.efficiency)
    print(f"📈 One year: demand ×{a.demand:g}/yr, efficiency ×{a.efficiency:g}/yr (IEA-based), total energy vs month 0")
    print(f"{'month':>5}  {'each job cheaper':>17}  {'effitrap cap':>12}  {'answered':>9}  {'full quality':>12}  {'rate limit answers':>18}")
    for r in rows:
        if r["month"] % 3 == 0:
            print(f"{r['month']:>5}  {r['A_total']:>16.2f}x  {r['B_total']:>11.2f}x  {r['B_served']*100:>8.0f}%  {r['B_full_quality']*100:>11.0f}%  {r['R_served']*100:>17.0f}%")
    last = rows[-1]
    print(f"🪤 Each-job-cheaper ends at {last['A_total']:.1f}x. The cap holds at ≤1.0x, "
          f"answering {last['B_served']*100:.0f}% ({last['B_full_quality']*100:.0f}% at full quality).")
    print(f"🚪 A rate limit with the SAME energy answers {last['R_served']*100:.0f}%. Bouncer vs knapsack.")


def cmd_pick(a):
    import os
    from .gate import Gate
    budget = a.budget if a.budget is not None else 1e12
    gate = Gate(budget_wh=budget, ledger_file=a.file if os.path.exists(a.file) or a.budget is not None else None)
    c = gate.pick(a.prompt, name=a.prompt[:40])
    if c.model is None:
        print(f"⏸ Wait: only {c.left_wh:g} Wh left this period. Try later or raise the budget.")
        return
    note = "" if c.full_quality else "  (budget is tight: smaller than ideal)"
    left = f" · {c.left_wh:g} Wh left" if c.left_wh < 1e11 else ""
    print(f"🧠 difficulty {c.difficulty:.2f} → use {c.model} ({c.wh:g} Wh){note}{left}")


def main(argv=None) -> int:
    p = argparse.ArgumentParser(prog="effitrap", description="Escape AI's efficiency trap. ⚡")
    p.add_argument("--version", action="version", version=f"effitrap {__version__}")
    sub = p.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("day", help="what a day of AI costs")
    s.add_argument("--texts", type=int, default=15)
    s.add_argument("--images", type=int, default=10)
    s.add_argument("--videos", type=int, default=3)
    s.set_defaults(fn=cmd_day)

    s = sub.add_parser("schedule", help="carbon-aware scheduling")
    s.add_argument("--energy", type=float, default=4.0, help="energy the job needs (in units of one slot at full power if --cap 1)")
    s.add_argument("--cap", type=float, default=1.0, help="max energy per slot")
    s.add_argument("--csv", help="file of intensities")
    s.add_argument("--gb", action="store_true", help="live Great Britain forecast")
    s.add_argument("--hours", type=int, default=24)
    s.set_defaults(fn=cmd_schedule)

    s = sub.add_parser("route", help="model routing")
    s.add_argument("--budget", type=float, default=10.0)
    s.add_argument("--requests", type=int, default=6)
    s.set_defaults(fn=cmd_route)

    s = sub.add_parser("batch", help="batch size")
    s.add_argument("--waste", type=float, default=0.7, help="KV-cache waste before paging (0..1)")
    s.add_argument("--fixed", type=float, default=100.0, help="fixed energy per step, J")
    s.add_argument("--marginal", type=float, default=5.0, help="extra energy per request per step, J")
    s.add_argument("--memory", type=float, default=80.0, help="accelerator memory, GB")
    s.add_argument("--weights", type=float, default=26.0, help="model weights, GB")
    s.add_argument("--kv", type=float, default=0.8, help="KV-cache per request, GB")
    s.add_argument("--sla", type=float, default=50.0, help="latency budget per step, ms")
    s.set_defaults(fn=cmd_batch)

    s = sub.add_parser("spec", help="speculative decoding")
    s.add_argument("--alpha", type=float, default=0.8)
    s.add_argument("--c", type=float, default=0.05)
    s.set_defaults(fn=cmd_spec)

    s = sub.add_parser("run", help="wait for the cleanest window, then run your command")
    s.add_argument("--hours", type=float, default=4.0, help="how long your job runs")
    s.add_argument("--within", type=float, default=24.0, help="deadline: start within this many hours")
    s.add_argument("--csv", help="file of intensities (one per slot)")
    s.add_argument("--slot-hours", type=float, default=1.0, help="slot length for --csv data")
    s.add_argument("--gb", action="store_true", help="live Great Britain forecast (half-hour slots)")
    s.add_argument("--zone", help="any Electricity Maps zone, e.g. DE (needs ELECTRICITYMAPS_TOKEN)")
    s.add_argument("--replan", type=float, default=30, help="re-check a live forecast every N minutes")
    s.add_argument("--dry-run", action="store_true", help="show the plan, don't run anything")
    s.add_argument("command", nargs=argparse.REMAINDER, help="-- your command")
    s.set_defaults(fn=cmd_run)

    s = sub.add_parser("budget", help="cap the total energy (anti-Jevons)")
    s.add_argument("action", choices=["set", "spend", "status"])
    s.add_argument("amount", type=float, nargs="?", default=0.0, help="Wh")
    s.add_argument("--name", default="job")
    s.add_argument("--file", default=LEDGER)
    s.set_defaults(fn=cmd_budget)

    s = sub.add_parser("pick", help="which AI brain to use for a prompt")
    s.add_argument("prompt")
    s.add_argument("--budget", type=float, default=None, help="start a budget (Wh) if none is set")
    s.add_argument("--file", default=".effitrap-budget.json")
    s.set_defaults(fn=cmd_pick)

    s = sub.add_parser("experiment", help="each-job-cheaper vs capped total")
    s.add_argument("--demand", type=float, default=15.0, help="demand growth per year")
    s.add_argument("--efficiency", type=float, default=10.0, help="per-task efficiency gain per year")
    s.set_defaults(fn=cmd_experiment)

    s = sub.add_parser("trap", help="the rebound bound")
    s.add_argument("--total", type=float, default=1.5)
    s.add_argument("--per-task", type=float, default=0.1)
    s.set_defaults(fn=cmd_trap)

    a = p.parse_args(argv)
    try:
        a.fn(a)
    except ValueError as e:
        print(f"❌ {e}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
