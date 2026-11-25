"""Move 3 - Time it: carbon-aware scheduling of a deferrable job.

Problem (fractional, single job):
    minimise   sum_t c[t] * x[t]
    subject to sum_t x[t] = E,   0 <= x[t] <= P   for every slot t

c[t]  carbon intensity of slot t (e.g. g CO2 per kWh)
x[t]  energy the job draws in slot t (kWh)
P     the most energy the job can draw in one slot (power cap x slot length)
E     total energy the job needs before its deadline

Greedy (fill cleanest slots first) is optimal by an exchange argument.
Two implementations:
    greedy_schedule  O(n log n)  sort, then fill
    linear_schedule  O(n) expected  quickselect the threshold, then one pass
Baselines from the literature (Dodge et al., FAccT 2022):
    run_now          start immediately, run flat out ("as soon as possible")
    flexible_start   choose the best contiguous window (sliding window, O(n))
"""
from __future__ import annotations

import math
import random
from typing import List, Sequence


def _check(c: Sequence[float], energy: float, cap: float) -> None:
    if cap <= 0:
        raise ValueError("cap must be positive")
    if energy < 0:
        raise ValueError("energy must be non-negative")
    if energy > cap * len(c) + 1e-9:
        raise ValueError(
            f"infeasible: job needs {energy} but {len(c)} slots x cap {cap} = {cap * len(c)}"
        )


def schedule_cost(c: Sequence[float], x: Sequence[float]) -> float:
    """Total emissions of schedule x: sum c[t] * x[t]."""
    return sum(ci * xi for ci, xi in zip(c, x))


def greedy_schedule(c: Sequence[float], energy: float, cap: float) -> List[float]:
    """Optimal schedule in O(n log n): sort slots by intensity, fill the cleanest first."""
    _check(c, energy, cap)
    x = [0.0] * len(c)
    remaining = energy
    for t in sorted(range(len(c)), key=lambda i: c[i]):
        if remaining <= 0:
            break
        take = min(cap, remaining)
        x[t] = take
        remaining -= take
    return x


def _quickselect(values: List[float], k: int, rng: random.Random) -> float:
    """k-th smallest (0-indexed) in expected O(n) time (randomised Hoare/Lomuto-free 3-way partition)."""
    while True:
        if len(values) == 1:
            return values[0]
        pivot = values[rng.randrange(len(values))]
        lows = [v for v in values if v < pivot]
        pivots = [v for v in values if v == pivot]
        if k < len(lows):
            values = lows
        elif k < len(lows) + len(pivots):
            return pivot
        else:
            k -= len(lows) + len(pivots)
            values = [v for v in values if v > pivot]


def linear_schedule(c: Sequence[float], energy: float, cap: float, seed: int = 0) -> List[float]:
    """Optimal schedule in expected O(n).

    Every slot has the same capacity, so the job fills the q = floor(E / P) cleanest
    slots and puts the remainder in the next one. Find the threshold intensity c* with
    quickselect, then assign in a single pass.
    """
    _check(c, energy, cap)
    n = len(c)
    x = [0.0] * n
    if energy == 0 or n == 0:
        return x
    full = min(n, math.ceil(energy / cap - 1e-12))  # number of slots touched
    # (when full == n every slot runs, but the PARTIAL one must still be the dirtiest,
    #  so the threshold logic below is used for that case too; the test suite caught this)
    threshold = _quickselect(list(c), full - 1, random.Random(seed))
    remaining = energy
    # strictly cleaner slots first (all of them are full)
    for t in range(n):
        if c[t] < threshold:
            x[t] = cap
            remaining -= cap
    # then slots exactly at the threshold, until the energy is used up
    for t in range(n):
        if remaining <= 1e-12:
            break
        if c[t] == threshold:
            take = min(cap, remaining)
            x[t] = take
            remaining -= take
    return x


def run_now(c: Sequence[float], energy: float, cap: float) -> List[float]:
    """Baseline: start immediately and run flat out."""
    _check(c, energy, cap)
    x = [0.0] * len(c)
    remaining = energy
    for t in range(len(c)):
        if remaining <= 0:
            break
        take = min(cap, remaining)
        x[t] = take
        remaining -= take
    return x


def flexible_start(c: Sequence[float], energy: float, cap: float) -> List[float]:
    """Baseline: pick the best start time, then run without pausing.

    Sliding window over window length L = ceil(E / P): O(n).
    """
    _check(c, energy, cap)
    n = len(c)
    length = max(1, math.ceil(energy / cap - 1e-12))
    best_start, window = 0, sum(c[:length])
    best = window
    for s in range(1, n - length + 1):
        window += c[s + length - 1] - c[s - 1]
        if window < best:
            best, best_start = window, s
    x = [0.0] * n
    remaining = energy
    for t in range(best_start, best_start + length):
        take = min(cap, remaining)
        x[t] = take
        remaining -= take
    return x
