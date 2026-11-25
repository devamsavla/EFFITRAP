"""Move 2 - Share (the big model's time): speculative decoding.

A small draft model proposes gamma tokens; the large model verifies them in ONE call
and keeps the longest accepted prefix plus one token of its own (Leviathan et al., ICML 2023).
If each draft token is accepted independently with probability alpha:

    E[tokens per large-model call] = sum_{i=0}^{gamma} alpha^i = (1 - alpha^(gamma+1)) / (1 - alpha)

With draft cost ratio c (time of one draft step / time of one large step), the expected
walltime improvement over plain decoding is

    speedup(alpha, gamma, c) = (1 - alpha^(gamma+1)) / ((1 - alpha) * (gamma * c + 1))

best_gamma scans gamma = 1..max_gamma (the function is unimodal in practice; a scan is
exact and cheap). simulate_tokens checks the closed form by Monte Carlo.
"""
from __future__ import annotations

import random


def expected_tokens(alpha: float, gamma: int) -> float:
    if not 0 <= alpha <= 1:
        raise ValueError("alpha must be in [0, 1]")
    if gamma < 0:
        raise ValueError("gamma must be >= 0")
    if alpha == 1:
        return gamma + 1.0
    return (1 - alpha ** (gamma + 1)) / (1 - alpha)


def speedup(alpha: float, gamma: int, c: float) -> float:
    return expected_tokens(alpha, gamma) / (gamma * c + 1)


def best_gamma(alpha: float, c: float, max_gamma: int = 16) -> int:
    return max(range(1, max_gamma + 1), key=lambda g: speedup(alpha, g, c))


def simulate_tokens(alpha: float, gamma: int, trials: int = 100_000, seed: int = 0) -> float:
    """Average tokens produced per large-model call, by simulation."""
    rng = random.Random(seed)
    total = 0
    for _ in range(trials):
        accepted = 0
        while accepted < gamma and rng.random() < alpha:
            accepted += 1
        total += accepted + 1  # the large model always contributes one token
    return total / trials
