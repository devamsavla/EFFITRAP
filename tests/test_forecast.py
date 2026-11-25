"""Forecast handling: real recorded data, other providers, wrong forecasts, failures, deadlines."""
import io
import json
import math
import os
import random

import pytest

from effitrap import flexible_start, run_now, schedule_cost
from effitrap import carbon
from effitrap.cli import best_start, wait_and_replan

FIX = os.path.join(os.path.dirname(__file__), "data", "gb_forecast_2026-11-24.json")


def _real():
    return json.load(open(FIX))


def test_parses_real_gb_forecast_recorded_2026_11_24():
    v = carbon.parse_gb(_real())
    assert len(v) == 97 and v[0] == 174 and min(v) == 66


def test_fetch_gb_uses_the_real_format(monkeypatch):
    class R(io.BytesIO):
        def __enter__(self): return self
        def __exit__(self, *a): pass
    monkeypatch.setattr(carbon.urllib.request, "urlopen", lambda req, timeout: R(json.dumps(_real()).encode()))
    assert carbon.fetch_gb_forecast(24)[:3] == [174, 171, 169] and len(carbon.fetch_gb_forecast(24)) == 48


def test_fetch_retries_then_reports_failure(monkeypatch):
    calls = []
    def boom(req, timeout):
        calls.append(1); raise OSError("no network")
    monkeypatch.setattr(carbon.urllib.request, "urlopen", boom)
    with pytest.raises(ConnectionError):
        carbon.fetch_gb_forecast()
    assert len(calls) == 3


def test_parses_electricitymaps_forecast_format():
    payload = {"zone": "DK-DK2", "forecast": [{"carbonIntensity": 101, "datetime": "2025-08-20T09:00:00.000Z"},
                                              {"carbonIntensity": 95, "datetime": "2025-08-20T10:00:00.000Z"}]}
    assert carbon.parse_electricitymaps(payload) == [101, 95]


def test_real_day_cleanest_4h_window():
    c = carbon.parse_gb(_real())[:48]                 # next 24 h from 16:00 UTC
    s = best_start(c, 8)                              # 4 h = 8 half-hours
    saving = 1 - schedule_cost(c, flexible_start(c, 8, 1)) / schedule_cost(c, run_now(c, 8, 1))
    assert s == 18 and round(saving, 2) == 0.56       # start 01:00 UTC, 56% less carbon


def test_plan_survives_wrong_forecasts():
    """Forecast off by up to ±30% in every slot: waiting still saves on average,
    and is rarely (and only slightly) worse than starting now."""
    savings = []
    for seed in range(300):
        r = random.Random(seed)
        need = r.randint(2, 12)
        phase = r.uniform(0, 48)
        truth = [max(20, 150 + 100 * math.sin((i + phase) / 48 * 2 * math.pi) + r.uniform(-20, 20)) for i in range(48)]
        forecast = [t * (1 + r.uniform(-0.3, 0.3)) for t in truth]
        plan = flexible_start(forecast, need, 1)
        savings.append(1 - schedule_cost(truth, plan) / schedule_cost(truth, run_now(truth, need, 1)))
    assert sum(savings) / len(savings) > 0.5            # measured: 54% average saving
    assert sum(s < 0 for s in savings) <= 0.03 * len(savings)   # measured: 8 of 300 worse than now
    assert min(savings) > -0.25                         # measured: worst case 22% worse


def test_replan_moves_the_start_when_the_forecast_changes():
    forecasts = iter([[300, 300, 300, 300, 300, 300, 50, 50],     # first: clean in 6 slots
                      [50, 50, 300, 300, 300, 300]])              # 2 slots later: clean now
    waited = wait_and_replan(lambda: next(forecasts), 2, 8, 1.0, 2, sleep=lambda s: None, log=lambda m: None)
    assert waited == 2


def test_no_forecast_at_all_starts_now():
    def fail(): raise ConnectionError("down")
    assert wait_and_replan(fail, 2, 8, 1.0, 2, sleep=lambda s: None, log=lambda m: None) == 0


def test_failure_mid_wait_keeps_the_last_plan():
    state = {"n": 0}
    def f():
        state["n"] += 1
        if state["n"] == 1:
            return [300, 300, 300, 300, 300, 300, 50, 50]
        raise ConnectionError("down")
    assert wait_and_replan(f, 2, 8, 1.0, 2, sleep=lambda s: None, log=lambda m: None) == 6


@pytest.mark.parametrize("seed", range(50))
def test_deadline_is_never_missed_even_if_forecasts_keep_changing(seed):
    r = random.Random(seed)
    slots, need = r.randint(4, 48), None
    need = r.randint(1, slots)
    waited = wait_and_replan(lambda: [r.uniform(20, 400) for _ in range(60)], need, slots, 0.5,
                             r.randint(1, 6), sleep=lambda s: None, log=lambda m: None)
    assert waited + need <= slots
