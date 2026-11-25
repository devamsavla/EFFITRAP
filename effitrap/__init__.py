"""effitrap: algorithms for escaping AI's efficiency trap.

Start here: effitrap.Gate, one line before each AI call (which brain, now or later, budget left).

Four moves, four modules:
    Do less   -> effitrap.router       (budgeted model routing, multiple-choice knapsack DP)
    Share     -> effitrap.batching     (amortised batching, optimal batch size by binary search)
                 effitrap.speculative  (speculative decoding: closed form + Monte Carlo)
    Time it   -> effitrap.schedule     (carbon-aware scheduling: greedy, O(n) selection, baselines)
    Show it   -> effitrap.identity     (E = sum N*w*eps decomposition, rebound bound)
                 effitrap.units        (Wh -> everyday equivalents)
"""

__version__ = "1.0.0"

from .schedule import greedy_schedule, linear_schedule, run_now, flexible_start, schedule_cost
from .router import Model, route_threshold, route_budgeted
from .batching import BatchConfig, cost_per_request, max_batch, best_batch
from .speculative import expected_tokens, speedup, best_gamma, simulate_tokens
from .identity import implied_demand_growth, decompose_growth, total_energy
from .units import everyday, day_of_ai
from .gate import CLAUDE_FAMILY, Gate, Choice, guess_difficulty

__all__ = [
    "greedy_schedule", "linear_schedule", "run_now", "flexible_start", "schedule_cost",
    "Model", "route_threshold", "route_budgeted",
    "BatchConfig", "cost_per_request", "max_batch", "best_batch",
    "expected_tokens", "speedup", "best_gamma", "simulate_tokens",
    "implied_demand_growth", "decompose_growth", "total_energy",
    "everyday", "day_of_ai",
    "Gate", "Choice", "guess_difficulty", "CLAUDE_FAMILY",
]
