"""Move 4+, the anti-Jevons move: cap the TOTAL, not just the cost per job.

Every existing green-AI tool makes each job cheaper (when to run, which model,
how to batch, how to measure). The rebound effect then turns cheaper jobs into
more jobs. effitrap's budget mode fixes the total energy for a period and lets an
optimiser decide how to spend it:

    maximise   total quality of the answers served
    subject to total energy <= budget

Each request may use any model, or be DEFERRED (no energy, no quality this period).
That is a multiple-choice knapsack, solved by dynamic programming (router.py).
Savings from efficiency then buy better answers, not unbounded growth.
"""
from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass, field
from typing import List, Optional, Sequence, Tuple

from .router import Model, route_budgeted

DEFER = Model("⏸ deferred", 0.0, 0.0)


@dataclass
class Ledger:
    """A simple energy budget for a period (e.g. a week), stored as JSON."""
    budget_wh: float
    spent_wh: float = 0.0
    jobs: List[dict] = field(default_factory=list)

    @property
    def left_wh(self) -> float:
        return max(0.0, self.budget_wh - self.spent_wh)

    def can_afford(self, wh: float) -> bool:
        return self.spent_wh + wh <= self.budget_wh + 1e-9

    def charge(self, name: str, wh: float) -> None:
        if not self.can_afford(wh):
            raise ValueError(f"over budget: {name} needs {wh:g} Wh, {self.left_wh:g} Wh left")
        self.spent_wh += wh
        self.jobs.append({"name": name, "wh": wh})

    def save(self, path: str) -> None:
        with open(path, "w") as f:
            json.dump(asdict(self), f, indent=2)

    @staticmethod
    def load(path: str) -> "Ledger":
        with open(path) as f:
            return Ledger(**json.load(f))


def serve_within_budget(
    options: Sequence[Sequence[Model]],
    budget_wh: float,
    resolution_wh: Optional[float] = None,
    allow_defer: bool = True,
) -> Tuple[float, List[Model]]:
    """Best total quality for these requests within budget_wh.

    With allow_defer, any request may be postponed (0 Wh, 0 quality), so a solution
    always exists. resolution_wh defaults to budget/2000 (B = 2000 knapsack units).
    """
    if budget_wh <= 0:
        return 0.0, [DEFER for _ in options]
    res = resolution_wh or budget_wh / 2000
    opts = [list(o) + ([DEFER] if allow_defer else []) for o in options]
    return route_budgeted(opts, budget_wh, res)
