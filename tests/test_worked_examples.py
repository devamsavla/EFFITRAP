"""The exact examples shown on the slides and in the paper."""
from effitrap.router import Model, route_budgeted


def test_greedy_by_value_per_wh_is_wrong_for_whole_jobs():
    jobs = [("A", 6, 7), ("B", 5, 5), ("C", 5, 5)]          # name, Wh, value; budget 10 Wh
    left, greedy = 10, 0
    for _, w, v in sorted(jobs, key=lambda j: -j[2] / j[1]):  # best value per Wh first
        if w <= left:
            left -= w
            greedy += v
    best, _ = route_budgeted([[Model("skip", 0, 0), Model(n, w, v)] for n, w, v in jobs], 10, 1)
    assert greedy == 7 and best == 10                          # greedy is 30% worse


def test_worked_backpack_table():
    qs = [(0.9, 1.0), (0.3, 1.0), (0.6, 0.9)]                  # (small, big) quality; small 1 Wh, big 3 Wh
    opts = [[Model("skip", 0, 0), Model("small", 1, s), Model("big", 3, b)] for s, b in qs]
    best, chosen = route_budgeted(opts, 5, 1)
    assert round(best, 2) == 2.5 and [c.name for c in chosen] == ["small", "big", "small"]
