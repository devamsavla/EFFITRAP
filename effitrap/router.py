"""Move 1 - Do less: send each request to the lightest model that is good enough.

Two routers:

route_threshold   For each request, the cheapest model whose quality meets the
                  request's required level. O(n * m). Simple and fast.

route_budgeted    Maximise total quality across a batch of requests under a total
                  energy budget B. This is the multiple-choice knapsack problem:
                  each request must take exactly one model ("one item per group").
                  Dynamic programming over energy in integer units:

                      best[i][b] = max over models j of
                                   best[i-1][b - cost_ij] + quality_ij

                  O(n * m * B) time, O(n * B) memory for reconstruction.
                  Pseudo-polynomial, like 0/1 knapsack (NP-hard in general).

Energy per request defaults come from the IEA (2025) lab tests, GPU only.
Quality scores are inputs you supply; the defaults in examples are illustrative.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import List, Optional, Sequence, Tuple


@dataclass(frozen=True)
class Model:
    name: str
    wh: float          # energy per request, watt-hours
    quality: float     # 0..1, how well it handles the request class (your input)


# IEA (2025), Figs. 1.16-1.17, GPU energy, test conditions.
IEA_MODELS = [
    Model("very-small (1.7B)", 0.1, 0.55),
    Model("small (9B)", 0.3, 0.70),
    Model("medium (70B)", 4.0, 0.85),
    Model("large reasoning", 8.0, 0.95),  # ~2x a same-size model (IEA); quality illustrative
]


def route_threshold(required: Sequence[float], models: Sequence[Model]) -> List[Optional[Model]]:
    """Cheapest adequate model per request (None if no model is good enough)."""
    by_cost = sorted(models, key=lambda m: m.wh)
    out: List[Optional[Model]] = []
    for need in required:
        out.append(next((m for m in by_cost if m.quality >= need), None))
    return out


def route_budgeted(
    options: Sequence[Sequence[Model]],
    budget_wh: float,
    resolution_wh: float = 0.1,
) -> Tuple[float, List[Model]]:
    """Multiple-choice knapsack: pick one model per request to maximise total quality
    with total energy <= budget_wh.

    options[i] lists the models request i may use (with their quality for that request).
    Energies are rounded UP to multiples of resolution_wh, so the budget is never exceeded.
    Returns (total_quality, chosen models). Raises ValueError if even the cheapest
    choices exceed the budget.
    """
    if resolution_wh <= 0:
        raise ValueError("resolution must be positive")
    B = int(budget_wh / resolution_wh + 1e-9)
    NEG = float("-inf")
    n = len(options)
    # round each energy UP to whole units, so the real total never exceeds the budget
    costs = [[math.ceil(m.wh / resolution_wh - 1e-9) for m in opts] for opts in options]
    best = [0.0] + [NEG] * B  # best[b] = max quality using exactly b units so far
    choice: List[List[int]] = []
    for i, opts in enumerate(options):
        new = [NEG] * (B + 1)
        pick = [-1] * (B + 1)
        for b in range(B + 1):
            if best[b] == NEG:
                continue
            for j, m in enumerate(opts):
                nb = b + costs[i][j]
                if nb <= B and best[b] + m.quality > new[nb]:
                    new[nb] = best[b] + m.quality
                    pick[nb] = j * (B + 1) + b  # encode (model index, previous budget)
        best = new
        choice.append(pick)
    end = max(range(B + 1), key=lambda b: best[b])
    if best[end] == NEG:
        raise ValueError("budget too small for even the cheapest model on every request")
    chosen: List[Model] = []
    b = end
    for i in range(n - 1, -1, -1):
        code = choice[i][b]
        j, prev = divmod(code, B + 1)
        chosen.append(options[i][j])
        b = prev
    chosen.reverse()
    return best[end], chosen
