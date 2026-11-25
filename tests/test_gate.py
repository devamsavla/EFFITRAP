import json

import pytest

from effitrap import Gate, guess_difficulty
from effitrap.cli import main


def test_easy_prompt_gets_small_brain_hard_gets_big():
    g = Gate(budget_wh=100)
    assert g.pick("translate hello to French").model in ("tiny", "small")
    assert g.pick(0.9).model == "big"


def test_tight_budget_downgrades_then_waits():
    g = Gate(budget_wh=4.5)
    first = g.pick(0.9)                 # big (8 Wh) unaffordable -> medium (4 Wh)
    assert first.model == "medium" and not first.full_quality
    second = g.pick(0.2)
    assert second.model == "tiny"       # 0.5 Wh left
    while True:
        c = g.pick(0.2)
        if c.model is None:
            break
    assert g.ledger.spent_wh <= 4.5 + 1e-9


@pytest.mark.parametrize("budget", [1, 5, 20, 60])
def test_pick_many_never_over_budget_and_beats_first_come(budget):
    reqs = [0.2, 0.9, 0.5, 0.75, 0.3, 0.95, 0.6, 0.1] * 3
    g = Gate(budget_wh=budget)
    chosen = g.pick_many(reqs)
    assert g.ledger.spent_wh <= budget + 1e-9
    served = sum(c.model is not None for c in chosen)
    f = Gate(budget_wh=budget)          # first come, first served on the ideal model
    fcfs = 0
    for r in reqs:
        ideal = next(m for m in f.models if m.quality >= r) if r <= 0.95 else f.models[-1]
        if not f.ledger.can_afford(ideal.wh):
            break
        f.ledger.charge("x", ideal.wh); fcfs += 1
    assert served >= fcfs


def test_budget_persists_between_runs(tmp_path):
    p = str(tmp_path / "b.json")
    Gate(budget_wh=10, ledger_file=p).pick(0.9)
    g2 = Gate(budget_wh=999, ledger_file=p)          # loads the saved ledger
    assert g2.ledger.budget_wh == 10 and g2.ledger.spent_wh == 8.0


def test_guess_difficulty_in_range_and_ordered():
    assert 0 <= guess_difficulty("") <= 1
    assert guess_difficulty("prove this theorem about graphs") > guess_difficulty("translate hello")


def test_cli_pick(capsys, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    assert main(["pick", "Summarise this email", "--budget", "50"]) in (0, None)
    out = capsys.readouterr().out
    assert "use" in out and "Wh left" in out
    assert json.load(open(tmp_path / ".effitrap-budget.json"))["spent_wh"] > 0
