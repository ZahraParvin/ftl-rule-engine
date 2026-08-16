from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

ROSTERS = Path(__file__).resolve().parent / "rosters"
SCHEMES = ROOT / "schemes"


@pytest.fixture
def load():
    from ftl.model import Roster

    def _load(name: str) -> Roster:
        return Roster.from_json(ROSTERS / f"{name}.json")

    return _load


@pytest.fixture
def scheme():
    from ftl.limits import load_scheme

    def _scheme(name: str = "easa_base"):
        return load_scheme(name, SCHEMES)

    return _scheme


@pytest.fixture
def check(load, scheme):
    """Return the violations for a fixture roster under a scheme."""
    from ftl.engine import evaluate, violations

    def _check(roster_name: str, scheme_name: str = "easa_base"):
        return violations(evaluate(load(roster_name), scheme(scheme_name)))

    return _check


def fired(results, rule_id: str) -> bool:
    return any(r.rule_id == rule_id for r in results)
