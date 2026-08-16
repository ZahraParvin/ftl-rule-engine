"""Rolling-window aggregation for the cumulative ORO.FTL.210 limits.

"Any 7 consecutive days" is a sliding window anchored anywhere, not a calendar
week. A roster can have no calendar week over 60 duty hours and still be illegal.

polars does the sliding aggregation; the worst window always begins at a duty, so
anchoring on duty start times is sufficient.
"""
from __future__ import annotations

from datetime import timedelta

import polars as pl

from .model import Roster


def duty_frame(roster: Roster) -> pl.DataFrame:
    return pl.DataFrame(
        {
            "report": [d.report.replace(tzinfo=None) for d in roster.duties],
            "duty_h": [d.duty_time.total_seconds() / 3600 for d in roster.duties],
            "block_h": [d.block_time.total_seconds() / 3600 for d in roster.duties],
        }
    ).sort("report")


def rolling_totals(roster: Roster, days: int) -> pl.DataFrame:
    """Duty and block hours in the `days`-day window starting at each duty.

    TODO(rule): implement with pl.DataFrame.rolling over "report" with
    period=f"{days}d". Two things to get right:

      * The window must look FORWARD from each duty start, not backward. The
        regulation limits any consecutive period, and anchoring forward from
        each duty start covers every window that could be worst.
      * The interval is half-open. A duty landing exactly on the far boundary
        belongs to the next window, not this one, and counting it in both
        double-counts. Check `closed=` carefully.

    Returns a frame with columns: report, duty_window, block_window.

    See tests/test_cumulative.py::test_sliding_window_beats_calendar_week.
    """
    raise NotImplementedError("rolling_totals")


def dedupe_overlapping(results: list, key=lambda r: r.subject) -> list:
    """Collapse repeated reports of the same window so a planner sees one row."""
    seen: set = set()
    out = []
    for r in results:
        k = key(r)
        if k in seen:
            continue
        seen.add(k)
        out.append(r)
    return out
