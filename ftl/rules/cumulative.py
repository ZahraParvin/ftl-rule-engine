"""ORO.FTL.210 -- cumulative duty and flight time limits."""
from __future__ import annotations

from ..engine import Context, Level, RuleResult, rule
from ..model import Roster
from ..windows import dedupe_overlapping, rolling_totals


CUMULATIVE_RULES = [
    # (limit key, days, column, rule id, title)
    ("max_duty_7_days",   7,  "duty_window",  "ORO.FTL.210(a)(1)", "Maximum duty in 7 consecutive days"),
    ("max_duty_14_days",  14, "duty_window",  "ORO.FTL.210(a)(2)", "Maximum duty in 14 consecutive days"),
    ("max_duty_28_days",  28, "duty_window",  "ORO.FTL.210(a)(3)", "Maximum duty in 28 consecutive days"),
    ("max_block_28_days", 28, "block_window", "ORO.FTL.210(b)(1)", "Maximum flight time in 28 consecutive days"),
]


@rule(level=Level.ROSTER, id="ORO.FTL.210", title="Cumulative duty and flight time")
def cumulative_limits(roster: Roster, ctx: Context) -> list[RuleResult]:
    """Every rolling duty and block limit in one pass.

    TODO(rule): for each entry in CUMULATIVE_RULES, resolve the limit from the
    scheme (ctx.scheme.resolve(key)), call rolling_totals(roster, days), and emit
    a RuleResult per window that exceeds it.

    Report the WINDOW, not the duty: "56:15 in the 7 days from 2026-09-08" tells
    a planner where to cut. "Duty 7 is illegal" does not.

    Set binding_source from the resolved Limit so the report can say whether the
    regulation or the agreement bound it, and dedupe overlapping windows.
    """
    raise NotImplementedError("cumulative_limits")


@rule(level=Level.ROSTER, id="ORO.FTL.210(b)(2)",
      title="Maximum flight time in a calendar year")
def block_calendar_year(roster: Roster, ctx: Context) -> list[RuleResult]:
    """<= 900 h block in any calendar year.

    TODO(rule): calendar year, not a rolling window -- group by year and sum.
    """
    raise NotImplementedError("block_calendar_year")


@rule(level=Level.ROSTER, id="ORO.FTL.210(b)(3)",
      title="Maximum flight time in 12 consecutive months")
def block_12_months(roster: Roster, ctx: Context) -> list[RuleResult]:
    """<= 1000 h block in any 12 consecutive calendar months.

    TODO(rule): consecutive calendar months, so the window edges land on month
    boundaries -- not a 365-day rolling window.
    """
    raise NotImplementedError("block_12_months")
