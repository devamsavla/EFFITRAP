"""Move 4 - Show it: the energy identity and the rebound bound.

    E = sum_k N_k * w_k * eps        (tasks x work per task x energy per unit work)
    C = sum_t E_t * c_t              (energy x carbon intensity)

Per-task energy e_k = w_k * eps. If total energy grows by factor G_E while per-task
energy shrinks by factor G_e (< 1), task-weighted demand must have grown by G_E / G_e.
"""
from __future__ import annotations

import math
from typing import Dict, Sequence


def total_energy(n: Sequence[float], w: Sequence[float], eps: float) -> float:
    return sum(ni * wi for ni, wi in zip(n, w)) * eps


def implied_demand_growth(total_growth: float, per_task_factor: float) -> float:
    """e.g. total x1.5 while per-task energy x0.1  ->  demand x15."""
    if per_task_factor <= 0:
        raise ValueError("per-task factor must be positive")
    return total_growth / per_task_factor


def decompose_growth(n_growth: float, mix_growth: float, w_growth: float, eps_growth: float) -> Dict[str, float]:
    """Log-additive decomposition: ln G_E = ln G_N + ln G_mix + ln G_w + ln G_eps."""
    parts = {"tasks": n_growth, "mix": mix_growth, "work_per_task": w_growth, "energy_per_work": eps_growth}
    logs = {k: math.log(v) for k, v in parts.items()}
    total = sum(logs.values())
    return {"total_factor": math.exp(total), **{f"log_{k}": v for k, v in logs.items()}}
