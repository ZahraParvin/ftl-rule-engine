"""ORO.FTL.210 -- rolling duty and flight time windows."""
from __future__ import annotations

from datetime import timedelta

from conftest import fired
from ftl.windows import rolling_totals


def test_sliding_window_beats_calendar_week(check):
    """60:33 in a sliding 7-day window, no calendar week over 60:00.

    Grouping by calendar week passes this roster. That is the bug the fixture
    exists to catch: the regulation limits ANY 7 consecutive days.
    """
    assert fired(check("illegal_rolling_7day"), "ORO.FTL.210")


def test_rolling_totals_window_is_half_open(load):
    """A duty landing exactly on the far boundary belongs to the next window.

    Counting it in both double-counts and invents violations that are not there.
    """
    roster = load("illegal_rolling_7day")
    df = rolling_totals(roster, days=7)
    assert set(df.columns) >= {"report", "duty_window", "block_window"}
    assert len(df) == len(roster.duties)

    # Seven daily duties of 8:39; the window opening at the first duty holds all
    # seven. The eighth day is outside it.
    assert df["duty_window"].max() > 60.0
    assert df["duty_window"].max() < 61.0


def test_violation_names_the_window_not_the_duty(check):
    """A planner needs to know where to cut, which means the window."""
    v = check("illegal_rolling_7day")
    remark = next(r.remark for r in v if r.rule_id == "ORO.FTL.210")
    assert "7 days" in remark or "7-day" in remark, \
        f"name the window in the remark: {remark!r}"
    assert "60:00" in remark, f"name the limit in the remark: {remark!r}"


def test_operator_a_tightens_the_seven_day_limit(check):
    """Under a 55:00 CBA limit the 49:00 RexRest roster is still legal, but the
    60:33 roster is bound by the agreement rather than the regulation."""
    v = check("illegal_rolling_7day", "operator_a")
    hit = next(r for r in v if r.rule_id == "ORO.FTL.210")
    assert "Operator A" in hit.binding_source, \
        f"the CBA is the binding source at 55:00, got {hit.binding_source!r}"


def test_legal_tight_has_no_cumulative_violation(check):
    assert not fired(check("legal_tight"), "ORO.FTL.210")
