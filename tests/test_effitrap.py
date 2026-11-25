import itertools
import random
import sys

import pytest

from effitrap import (
    BatchConfig, Model, best_batch, best_gamma, cost_per_request, day_of_ai,
    decompose_growth, expected_tokens, flexible_start, greedy_schedule,
    implied_demand_growth, linear_schedule, max_batch, route_budgeted,
    route_threshold, run_now, schedule_cost, simulate_tokens, speedup,
)
from effitrap.cli import main as cli_main
from effitrap.router import IEA_MODELS

try:
    from scipy.optimize import linprog
except ImportError:  # pragma: no cover
    linprog = None


# ---------------- Move 3: scheduling ----------------

def _instance(rng, n=None):
    n = n or rng.randint(1, 40)
    c = [rng.choice([rng.uniform(20, 400), float(rng.randint(1, 5) * 50)]) for _ in range(n)]  # includes ties
    cap = rng.uniform(0.5, 3)
    energy = rng.uniform(0, n * cap)
    return c, energy, cap


def _feasible(x, energy, cap):
    return abs(sum(x) - energy) < 1e-6 and all(-1e-9 <= v <= cap + 1e-9 for v in x)


@pytest.mark.parametrize("seed", range(300))
def test_greedy_and_linear_agree_and_are_feasible(seed):
    rng = random.Random(seed)
    c, e, p = _instance(rng)
    g, l = greedy_schedule(c, e, p), linear_schedule(c, e, p, seed=seed)
    assert _feasible(g, e, p) and _feasible(l, e, p)
    assert schedule_cost(c, g) == pytest.approx(schedule_cost(c, l), rel=1e-9, abs=1e-9)


@pytest.mark.skipif(linprog is None, reason="scipy not installed")
@pytest.mark.parametrize("seed", range(100))
def test_greedy_matches_linear_programming_oracle(seed):
    rng = random.Random(1000 + seed)
    c, e, p = _instance(rng)
    res = linprog(c, A_eq=[[1.0] * len(c)], b_eq=[e], bounds=[(0, p)] * len(c), method="highs")
    assert res.success
    assert schedule_cost(c, greedy_schedule(c, e, p)) == pytest.approx(res.fun, rel=1e-7, abs=1e-6)


@pytest.mark.parametrize("seed", range(100))
def test_exchange_property_holds(seed):
    """No slot gets energy while a strictly cleaner slot has room (the proof's invariant)."""
    c, e, p = _instance(random.Random(2000 + seed))
    x = linear_schedule(c, e, p)
    for i in range(len(c)):
        for j in range(len(c)):
            if c[i] < c[j] and x[j] > 1e-9:
                assert x[i] >= p - 1e-9


@pytest.mark.parametrize("seed", range(100))
def test_baselines_never_beat_optimal(seed):
    c, e, p = _instance(random.Random(3000 + seed))
    opt = schedule_cost(c, greedy_schedule(c, e, p))
    assert schedule_cost(c, run_now(c, e, p)) >= opt - 1e-9
    assert schedule_cost(c, flexible_start(c, e, p)) >= opt - 1e-9


def test_schedule_edge_cases():
    assert greedy_schedule([5, 1], 0, 1) == [0, 0]
    assert linear_schedule([5, 1, 3], 3, 1) == [1, 1, 1]          # everything must run
    assert linear_schedule([7, 7, 7], 1.5, 1) == pytest.approx([1, 0.5, 0])  # ties
    with pytest.raises(ValueError):
        greedy_schedule([1, 2], 5, 1)                               # infeasible
    with pytest.raises(ValueError):
        linear_schedule([1], 1, 0)                                  # zero cap


def test_sample_day_saving_is_large():
    from effitrap.carbon import SAMPLE_DAY
    now = schedule_cost(SAMPLE_DAY, run_now(SAMPLE_DAY, 4, 1))
    best = schedule_cost(SAMPLE_DAY, linear_schedule(SAMPLE_DAY, 4, 1))
    assert best < 0.25 * now


# ---------------- Move 1: routing ----------------

def _brute_force(options, budget, res):
    best = None
    import math
    for combo in itertools.product(*options):
        if sum(math.ceil(m.wh / res - 1e-9) for m in combo) <= round(budget / res):
            q = sum(m.quality for m in combo)
            best = q if best is None else max(best, q)
    return best


@pytest.mark.parametrize("seed", range(120))
def test_budgeted_router_matches_brute_force(seed):
    rng = random.Random(seed)
    n, m = rng.randint(1, 5), rng.randint(1, 4)
    options = [[Model(f"m{j}", round(rng.uniform(0.1, 5), 1), round(rng.uniform(0, 1), 2)) for j in range(m)]
               for _ in range(n)]
    cheapest = sum(min(o.wh for o in opts) for opts in options)
    budget = round(rng.uniform(cheapest, cheapest + 10), 1)
    q, chosen = route_budgeted(options, budget, 0.1)
    assert q == pytest.approx(_brute_force(options, budget, 0.1))
    assert sum(c.wh for c in chosen) <= budget + 1e-9
    assert len(chosen) == n


def test_router_budget_too_small():
    with pytest.raises(ValueError):
        route_budgeted([[Model("a", 5, 1)]], 1)


def test_threshold_router_picks_cheapest_adequate():
    picks = route_threshold([0.5, 0.8, 0.99], IEA_MODELS)
    assert picks[0].name.startswith("very-small")
    assert picks[1].name.startswith("medium")
    assert picks[2] is None


# ---------------- Move 2: batching ----------------

@pytest.mark.parametrize("waste", [0.0, 0.3, 0.62, 0.8])
@pytest.mark.parametrize("sla", [20, 25, 50, 100, 400])
def test_best_batch_equals_linear_scan(waste, sla):
    cfg = BatchConfig(waste=waste, sla_ms=sla)
    feasible = [b for b in range(1, max_batch(cfg) + 1) if cfg.t0_ms + cfg.t1_ms * b <= cfg.sla_ms]
    assert best_batch(cfg) == (max(feasible) if feasible else 0)


def test_paging_raises_batch_and_cuts_cost():
    before, after = BatchConfig(waste=0.7, sla_ms=1e9), BatchConfig(waste=0.04, sla_ms=1e9)
    assert max_batch(after) > 2 * max_batch(before)
    assert cost_per_request(best_batch(after), after) < cost_per_request(best_batch(before), before)


def test_amortised_cost_is_decreasing_with_diminishing_returns():
    cfg = BatchConfig()
    costs = [cost_per_request(b, cfg) for b in (1, 2, 4, 8, 16)]
    saves = [a - b for a, b in zip(costs, costs[1:])]
    assert all(s > 0 for s in saves) and all(x > y for x, y in zip(saves, saves[1:]))


# ---------------- speculative decoding ----------------

@pytest.mark.parametrize("alpha,gamma", [(0.5, 3), (0.8, 4), (0.9, 8), (0.3, 1)])
def test_formula_matches_simulation(alpha, gamma):
    assert simulate_tokens(alpha, gamma, 200_000, seed=7) == pytest.approx(expected_tokens(alpha, gamma), rel=0.01)


def test_speculative_known_values():
    assert expected_tokens(0.8, 4) == pytest.approx(3.3616)
    assert expected_tokens(1.0, 4) == 5
    assert expected_tokens(0.0, 4) == 1
    g = best_gamma(0.8, 0.05)
    assert all(speedup(0.8, g, 0.05) >= speedup(0.8, k, 0.05) for k in range(1, 17))


# ---------------- Move 4: identity and units ----------------

def test_identity():
    assert implied_demand_growth(1.5, 0.1) == pytest.approx(15)
    d = decompose_growth(3, 2, 0.1, 0.5)
    assert d["total_factor"] == pytest.approx(0.3)


def test_day_of_ai_addition():
    d = day_of_ai()
    assert d["wh"] == pytest.approx(15 * 0.3 + 10 * 1.7 + 3 * 115)  # 366.5 Wh
    assert d["kwh"] == pytest.approx(0.3665)
    assert d["laptop_charges"] == pytest.approx(366.5 / 60)


# ---------------- product surface ----------------

@pytest.mark.parametrize("args", [["day"], ["schedule"], ["route"], ["batch"], ["spec"], ["trap"]])
def test_cli_commands_run(args, capsys):
    assert cli_main(args) == 0
    assert capsys.readouterr().out.strip()


def test_cli_run_dry_run_plans_the_sunny_window(capsys):
    assert cli_main(["run", "--hours", "4", "--dry-run", "--", "python", "train.py"]) == 0
    out = capsys.readouterr().out
    assert "starts in 12 h" in out and "77% less" in out and "Dry run" in out


def test_cli_run_executes_command_when_best_window_is_now(tmp_path, capsys):
    grid = tmp_path / "grid.csv"
    grid.write_text("50\n60\n300\n300\n")
    marker = tmp_path / "ran.txt"
    cmd = [sys.executable, "-c", f"open(r'{marker}', 'w').write('ok')"]
    assert cli_main(["run", "--hours", "2", "--within", "4", "--csv", str(grid), "--"] + cmd) == 0
    assert marker.read_text() == "ok"


def test_cli_batch_accepts_custom_numbers(capsys):
    assert cli_main(["batch", "--memory", "40", "--weights", "14", "--kv", "0.5", "--sla", "30"]) == 0


def test_cli_reports_infeasible(capsys):
    assert cli_main(["schedule", "--energy", "999"]) == 1


def test_api():
    pytest.importorskip("fastapi")
    pytest.importorskip("httpx")
    from fastapi.testclient import TestClient
    from effitrap.api import app
    client = TestClient(app)
    assert client.get("/health").json()["ok"]
    r = client.post("/schedule", json={"intensities": [300, 70, 65, 280], "energy": 2, "cap": 1})
    assert r.status_code == 200 and r.json()["optimal"]["x"] == [0, 1, 1, 0]
    assert client.post("/schedule", json={"intensities": [1], "energy": 5, "cap": 1}).status_code == 422
    r = client.post("/route", json={"budget_wh": 1, "requests": [[{"name": "s", "wh": 0.3, "quality": 0.7},
                                                                  {"name": "m", "wh": 4, "quality": 0.85}]]})
    assert r.json()["chosen"] == ["s"]
    assert client.get("/day").json()["wh"] == pytest.approx(366.5)


# ---------------- budget mode (anti-Jevons) ----------------

from effitrap.budget import DEFER, Ledger, serve_within_budget
from effitrap.experiment import run as run_experiment


def test_ledger_caps_total(tmp_path):
    led = Ledger(budget_wh=100)
    led.charge("a", 60)
    with pytest.raises(ValueError):
        led.charge("b", 50)
    p = tmp_path / "l.json"; led.save(str(p))
    assert Ledger.load(str(p)).left_wh == pytest.approx(40)


@pytest.mark.parametrize("seed", range(60))
def test_budget_serving_matches_brute_force_with_defer(seed):
    import math
    rng = random.Random(seed)
    n = rng.randint(1, 4)
    opts = [[Model(f"m{j}", round(rng.uniform(0.1, 3), 1), round(rng.uniform(0, 1), 2)) for j in range(3)] for _ in range(n)]
    budget = round(rng.uniform(0, 6), 1)
    q, chosen = serve_within_budget(opts, budget, resolution_wh=0.1)
    best = 0.0
    for combo in itertools.product(*[o + [DEFER] for o in opts]):
        if sum(math.ceil(m.wh / 0.1 - 1e-9) for m in combo) <= round(budget / 0.1):
            best = max(best, sum(m.quality for m in combo))
    assert q == pytest.approx(best)
    assert sum(m.wh for m in chosen) <= budget + 1e-9


def test_experiment_cap_holds_and_each_job_cheaper_grows():
    rows = run_experiment()
    assert rows[-1]["A_total"] == pytest.approx(1.5, rel=1e-6)   # 15x demand / 10x efficiency
    assert all(r["B_total"] <= 1.0 + 1e-9 for r in rows)          # cap never broken
    assert rows[-1]["B_served"] == 1.0 and rows[-1]["B_full_quality"] >= 0.9


def test_experiment_forces_visible_choice_when_demand_explodes():
    last = run_experiment(demand_per_year=60)[-1]
    assert last["B_total"] <= 1.0 + 1e-9 and last["B_served"] < 1.0


@pytest.mark.parametrize("demand", [15, 30, 60, 120])
def test_knapsack_beats_rate_limit_on_same_energy(demand):
    """Same cap, same requests: choosing what to spend on never answers fewer people
    than first-come-first-served (what AI apps' rate limits do)."""
    for r in run_experiment(demand_per_year=demand):
        assert r["B_total"] <= 1.0 + 1e-9
        assert r["B_served"] >= r["R_served"]


@pytest.mark.parametrize("args", [["experiment"], ["budget", "status", "--file", "nope.json"]])
def test_cli_budget_and_experiment(args, capsys, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    rc = cli_main(args)
    assert rc == (0 if args[0] == "experiment" else 1)


def test_cli_budget_flow(tmp_path, capsys):
    f = str(tmp_path / "b.json")
    assert cli_main(["budget", "set", "100", "--file", f]) == 0
    assert cli_main(["budget", "spend", "85", "--name", "train", "--file", f]) == 0
    out = capsys.readouterr().out
    assert "85% used" in out and "Running low" in out
    assert cli_main(["budget", "spend", "50", "--file", f]) == 1
