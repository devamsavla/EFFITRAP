"""The gate: one line before each AI call.

effitrap does not change the AI model. It sits between your app and the AI and
answers three questions before each call:

    which brain?   the smallest model that is good enough for this request
    now or later?  if the energy budget can't afford it, use a smaller brain or wait
    how much left? a running total of energy spent against your budget

    from effitrap import Gate
    gate = Gate(budget_wh=5000)                  # e.g. this week's AI energy
    choice = gate.pick("Summarise this email")   # -> Choice(model='small', wh=0.3, ...)
    if choice.model:
        answer = call_my_ai(choice.model, prompt)  # your existing code, unchanged

For a batch of requests, pick_many() solves the exact knapsack: everyone gets the
best answer the budget allows.

Difficulty: pass your own score in [0, 1] (e.g. from a trained router such as
RouteLLM), or let guess_difficulty() estimate it from the prompt. The guess is a
deliberately simple heuristic, meant to be replaced.
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from typing import List, Optional, Sequence, Union

from .budget import DEFER, Ledger, serve_within_budget
from .router import Model

DEFAULT_MODELS = [  # energy per answer from IEA (2025) lab tests; quality illustrative
    Model("tiny", 0.1, 0.55), Model("small", 0.3, 0.70),
    Model("medium", 4.0, 0.85), Model("big", 8.0, 0.95)]

import re

# Claude only? It's already a family. Anthropic doesn't publish energy per answer, so these
# are stand-ins from the IEA's small / medium / large lab measurements. Replace if you measure.
CLAUDE_FAMILY = [Model("claude-haiku-5-5", 0.3, 0.70), Model("claude-sonnet-5-5", 4.0, 0.85),
                 Model("claude-opus-5-5", 8.0, 0.95)]

_HARD = ("prove", "proof", "theorem", "derive", "analyse", "analyze", "debug", "design", "plan",
         "why", "compare", "research", "optimise", "optimize", "essay", "code", "legal",
         "medical", "diagnose", "strategy")
_EASY = ("translate", "define", "spell", "convert", "hi", "hello", "thanks", "summarise",
         "summarize", "reply", "rewrite", "what's")


def guess_difficulty(prompt: str) -> float:
    """Rough difficulty in [0, 1] from length and whole-word keywords.
    Deliberately simple: replace with a trained router for real use."""
    words = re.findall(r"[a-z']+", prompt.lower())
    stems = set(words)
    hard = sum(1 for w in words if any(w.startswith(k) for k in _HARD))
    easy = sum(1 for k in _EASY if k in stems or any(w.startswith(k) for w in words if len(k) > 4))
    d = 0.35 + min(len(prompt), 2000) / 2000 * 0.35 + 0.35 * min(hard, 2) - 0.15 * min(easy, 2)
    return max(0.0, min(0.99, d))


@dataclass
class Choice:
    model: Optional[str]     # None = wait (budget can't afford even the smallest brain)
    wh: float
    difficulty: float
    full_quality: bool       # False if the budget forced a smaller brain than ideal
    left_wh: float


class Gate:
    def __init__(self, budget_wh: float, models: Sequence[Model] = DEFAULT_MODELS,
                 ledger_file: Optional[str] = None):
        self.models = sorted(models, key=lambda m: m.wh)
        self.ledger_file = ledger_file
        if ledger_file and os.path.exists(ledger_file):
            self.ledger = Ledger.load(ledger_file)
        else:
            self.ledger = Ledger(budget_wh)

    def _need(self, request: Union[str, float]) -> float:
        return float(request) if isinstance(request, (int, float)) else guess_difficulty(request)

    def pick(self, request: Union[str, float], name: str = "request") -> Choice:
        """Choose a brain for one request and charge the budget."""
        need = self._need(request)
        ideal = next((m for m in self.models if m.quality >= need), self.models[-1])
        if self.ledger.can_afford(ideal.wh):
            m, full = ideal, True
        else:
            affordable = [m for m in self.models if self.ledger.can_afford(m.wh)]
            if not affordable:
                return Choice(None, 0.0, need, False, self.ledger.left_wh)
            m, full = affordable[-1], affordable[-1].quality >= need
        self.ledger.charge(f"{name} -> {m.name}", m.wh)
        if self.ledger_file:
            self.ledger.save(self.ledger_file)
        return Choice(m.name, m.wh, need, full, self.ledger.left_wh)

    def pick_many(self, requests: Sequence[Union[str, float]]) -> List[Choice]:
        """Choose brains for a batch so the remaining budget covers as many as possible,
        as well as possible (exact multiple-choice knapsack)."""
        needs = [self._need(r) for r in requests]
        options = [[Model(m.name, m.wh, 1.0 if m.quality >= n else max(0.0, 1 - (n - m.quality) * 2.5))
                    for m in self.models] for n in needs]
        _, chosen = serve_within_budget(options, self.ledger.left_wh)
        out = []
        base = {m.name: m for m in self.models}
        for n, m in zip(needs, chosen):
            if m.name == DEFER.name or m.wh == 0:
                out.append(Choice(None, 0.0, n, False, self.ledger.left_wh))
                continue
            self.ledger.charge(m.name, m.wh)
            out.append(Choice(m.name, m.wh, n, base[m.name].quality >= n, self.ledger.left_wh))
        if self.ledger_file:
            self.ledger.save(self.ledger_file)
        return out
