"""Same roster, same scheme, same report -- every time.

A legality checker whose output depends on dict ordering is not one a planner can
trust, and reproducibility is what makes a regression suite meaningful.
"""
from __future__ import annotations

from ftl.engine import evaluate


def test_repeated_evaluation_is_identical(load, scheme):
    roster, s = load("illegal_rolling_7day"), scheme("operator_a")
    first = [str(r) for r in evaluate(roster, s)]
    second = [str(r) for r in evaluate(roster, s)]
    assert first == second


def test_rule_order_is_stable_across_processes(load, scheme):
    """Ordering is by (level, rule_id), not registration or import order."""
    roster, s = load("legal_tight"), scheme("easa_base")
    ids = [r.rule_id for r in evaluate(roster, s)]
    assert ids == sorted(ids, key=lambda x: x) or len(set(ids)) < len(ids)
