"""Move 2 - Share: batching as amortisation.

Each decoding step pays a fixed cost F (streaming the weights from memory) no matter
how many requests share it, plus a marginal cost v per request:

    cost_per_request(b) = F / b + v                       (amortised analysis)

Constraints:
    memory   b <= floor((M - W) / (m / (1 - waste)))      KV-cache per request m,
                                                          fragmentation waste in [0, 1)
    latency  step_time(b) = t0 + t1 * b <= SLA            (a simple linear model)

cost_per_request is decreasing in b and step_time is increasing, so the best batch is
the LARGEST feasible b, found by binary search on the monotone latency predicate:
O(log b_max) checks.

PagedAttention (Kwon et al., SOSP 2023) cuts KV-cache waste; conventional systems used only
20.4-38.2% of KV-cache memory for real token states. Set waste accordingly to see the effect.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class BatchConfig:
    fixed_j: float = 100.0       # F: fixed energy per step (J), illustrative
    marginal_j: float = 5.0      # v: extra energy per request per step (J), illustrative
    memory_gb: float = 80.0      # M: accelerator memory
    weights_gb: float = 26.0     # W: model weights
    kv_gb: float = 0.8           # m: useful KV-cache per request
    waste: float = 0.0           # fraction of KV memory lost to fragmentation (0..1)
    t0_ms: float = 20.0          # step time intercept
    t1_ms: float = 0.5           # step time per extra request
    sla_ms: float = 50.0         # latency budget per step


def cost_per_request(b: int, cfg: BatchConfig) -> float:
    if b < 1:
        raise ValueError("batch size must be >= 1")
    return cfg.fixed_j / b + cfg.marginal_j


def max_batch(cfg: BatchConfig) -> int:
    """Largest batch that fits in memory."""
    if not 0 <= cfg.waste < 1:
        raise ValueError("waste must be in [0, 1)")
    per_request = cfg.kv_gb / (1 - cfg.waste)
    return max(0, int((cfg.memory_gb - cfg.weights_gb) // per_request))


def _fits_latency(b: int, cfg: BatchConfig) -> bool:
    return cfg.t0_ms + cfg.t1_ms * b <= cfg.sla_ms


def best_batch(cfg: BatchConfig) -> int:
    """Largest batch meeting both memory and latency limits (binary search)."""
    hi = max_batch(cfg)
    if hi < 1 or not _fits_latency(1, cfg):
        return 0
    lo = 1  # invariant: lo is feasible
    while lo < hi:
        mid = (lo + hi + 1) // 2
        if _fits_latency(mid, cfg):
            lo = mid
        else:
            hi = mid - 1
    return lo
