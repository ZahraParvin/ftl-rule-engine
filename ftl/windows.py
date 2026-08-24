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
    """Duty and block hours in the forward `days`-day half-open window [t, t+days) starting at each duty.

    Forward-looking: the window opens at each duty's report time, not backward.
    Half-open: a duty landing exactly on the far boundary belongs to the next window.
    """
    from datetime import timedelta
    df = duty_frame(roster)
    period = timedelta(days=days)
    reports = df["report"].to_list()
    duty_h = df["duty_h"].to_list()
    block_h = df["block_h"].to_list()
    n = len(reports)

    duty_windows = []
    block_windows = []
    for i in range(n):
        cutoff = reports[i] + period
        duty_windows.append(sum(duty_h[j] for j in range(i, n) if reports[j] < cutoff))
        block_windows.append(sum(block_h[j] for j in range(i, n) if reports[j] < cutoff))

    return df.with_columns([
        pl.Series("duty_window", duty_windows),
        pl.Series("block_window", block_windows),
    ])


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
