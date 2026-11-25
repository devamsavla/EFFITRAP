"""The experiment: per-job efficiency vs a capped total, under rebound.

Growth rates come from the IEA (2026):
  * energy per AI task falls >= 10x per year       -> per-task factor 0.1^(t/12) per month
  * AI-focused data-centre electricity +50% in 2025  -> with 10x efficiency, task-weighted
                                                       demand must grow 1.5 / 0.1 = 15x per year
Model energies per answer come from IEA (2025) lab tests (0.1 / 0.3 / 4 / 8 Wh).
Request difficulty and model quality are ILLUSTRATIVE (stated, seeded, reproducible).

Policies, simulated monthly for one year on a representative sample of requests:
  A  "Each job cheaper" (today's tools): every request goes to the cheapest model that is
     good enough (a smart router). Efficiency improves, demand grows, nothing caps the total.
  R  "Rate limit" (what AI apps do today): same cap as B, but requests are served first-come,
     first-served on the cheapest adequate model until the budget runs out; the rest are refused.
  B  "effitrap budget": same requests, same efficiency, but total energy is capped at
     month-0 level. A knapsack chooses models, or defers requests, to maximise quality.
"""
from __future__ import annotations

import random
from typing import Dict, List

from .budget import serve_within_budget
from .router import Model

BASE_MODELS = [  # IEA (2025) lab energies; quality illustrative
    Model("tiny", 0.1, 0.55), Model("small", 0.3, 0.70),
    Model("medium", 4.0, 0.85), Model("big", 8.0, 0.95)]


def _requests(n: int, rng: random.Random) -> List[float]:
    """Difficulty in [0,1]: most questions are easy, a few are hard (illustrative)."""
    return [min(0.99, rng.betavariate(2, 3.2)) for _ in range(n)]


def _quality_for(need: float, m: Model) -> float:
    """Full credit if the model is good enough; partial credit if it falls short."""
    if m.wh == 0:
        return 0.0
    return 1.0 if m.quality >= need else max(0.0, 1 - (need - m.quality) * 2.5)


def run(months: int = 12, sample: int = 120, demand_per_year: float = 15.0,
        efficiency_per_year: float = 10.0, seed: int = 7) -> List[Dict[str, float]]:
    rng = random.Random(seed)
    needs = _requests(sample, rng)
    rows = []
    cap_total = None
    for t in range(months + 1):
        f = (1 / efficiency_per_year) ** (t / 12)          # per-task energy factor
        scale = demand_per_year ** (t / 12)                 # how many real requests one sample stands for
        models = [Model(m.name, m.wh * f, m.quality) for m in BASE_MODELS]
        # Policy A: cheapest adequate model per request
        a_wh = 0.0
        for need in needs:
            m = next((m for m in models if m.quality >= need), models[-1])
            a_wh += m.wh
        a_total = a_wh * scale
        if cap_total is None:
            cap_total = a_total                              # cap = month-0 level
        # Policy B: knapsack within the capped budget (per-sample share of the cap)
        options = [[Model(m.name, m.wh, _quality_for(need, m)) for m in models] for need in needs]
        q, chosen = serve_within_budget(options, cap_total / scale)
        b_total = sum(m.wh for m in chosen) * scale
        # Policy R: rate limit = same cap, first come first served, then "try again later"
        left = cap_total / scale
        r_served = 0
        for need in needs:
            m = next((m for m in models if m.quality >= need), models[-1])
            if m.wh <= left + 1e-12:
                left -= m.wh
                r_served += 1
            else:
                break
        served = sum(1 for m in chosen if m.wh > 0) / sample
        base = {m.name: m for m in BASE_MODELS}
        full = sum(1 for need, m in zip(needs, chosen) if m.wh > 0 and base[m.name].quality >= need) / sample
        avg_q = q / sample
        rows.append({
            "month": t,
            "A_total": a_total / cap_total,          # relative to month 0
            "B_total": b_total / cap_total,
            "B_served": served,
            "B_full_quality": full,
            "B_avg_quality": avg_q,
            "A_full_quality": 1.0,
            "R_served": r_served / sample,
        })
    return rows
