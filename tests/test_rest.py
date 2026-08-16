"""ORO.FTL.235 -- rest and recurrent extended recovery rest."""
from __future__ import annotations

from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import pytest

from conftest import fired
from ftl.timeutil import local_nights_between


def test_home_base_floor_binds(check):
    """A 9:00 preceding duty is shorter than the 12:00 floor, so the floor binds."""
    v = check("illegal_rest_home")
    assert fired(v, "ORO.FTL.235(a)")
    remark = next(r.remark for r in v if r.rule_id == "ORO.FTL.235(a)")
    assert "12:00" in remark, f"the remark must name the binding 12:00 floor: {remark!r}"


def test_away_base_preceding_duty_binds(check):
    """An 11:00 preceding duty beats the 10:00 floor away from base.

    Comparing only against the floor passes this roster, which is the bug.
    """
    v = check("illegal_rest_away")
    assert fired(v, "ORO.FTL.235(b)")
    remark = next(r.remark for r in v if r.rule_id == "ORO.FTL.235(b)")
    assert "11:00" in remark, \
        f"the preceding duty period, not the floor, is binding here: {remark!r}"


def test_home_base_rule_does_not_fire_on_away_duty(check):
    """235(a) and 235(b) are mutually exclusive -- pick by where the FDP starts."""
    assert not fired(check("illegal_rest_away"), "ORO.FTL.235(a)")


def test_rexrest_interval_over_168_hours(check):
    assert fired(check("illegal_rexrest_gap"), "ORO.FTL.235(d)")


def test_rexrest_short_across_spring_forward(check):
    """36:00 of wall clock across the March change is 35:00 of actual rest.

    Fixed UTC offsets pass this roster. zoneinfo arithmetic catches it.
    """
    assert fired(check("illegal_rexrest_dst"), "ORO.FTL.235(d)")


def test_legal_tight_has_no_rest_violation(check):
    v = check("legal_tight")
    assert not fired(v, "ORO.FTL.235(a)")
    assert not fired(v, "ORO.FTL.235(b)")


def test_legal_tight_has_no_violations_at_all(check):
    """The whole point of this fixture: tight, but clean."""
    assert check("legal_tight") == []


# --- local night counting ----------------------------------------------------

def _oslo(s: str) -> datetime:
    return datetime.strptime(s, "%Y-%m-%d %H:%M").replace(tzinfo=ZoneInfo("Europe/Oslo"))


@pytest.mark.parametrize("start,end,expected", [
    ("2026-09-01 20:00", "2026-09-03 09:00", 2),   # two full 22:00-08:00 windows
    ("2026-09-01 23:00", "2026-09-02 09:00", 0),   # started after 22:00, night incomplete
    ("2026-09-01 20:00", "2026-09-02 07:00", 0),   # ended before 08:00
    ("2026-09-01 20:00", "2026-09-02 08:00", 1),
    ("2027-03-27 20:00", "2027-03-29 08:00", 2),   # spans the spring-forward change
])
def test_local_nights_between(start, end, expected):
    assert local_nights_between(_oslo(start), _oslo(end), "Europe/Oslo") == expected
