"""ORO.FTL.210 -- cumulative duty and flight time limits."""
from __future__ import annotations

from datetime import timedelta

from ..engine import Context, Level, RuleResult, rule
from ..model import Roster
from ..timeutil import hm
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
    """Every rolling duty and block limit in one pass."""
    results = []
    for key, days, col, _rule_id, title in CUMULATIVE_RULES:
        limit = ctx.scheme.resolve(key)
        limit_h = limit.value.total_seconds() / 3600
        df = rolling_totals(roster, days)
        for row in df.filter(df[col] > limit_h).iter_rows(named=True):
            total_td = timedelta(hours=row[col])
            window_start = row["report"].strftime("%Y-%m-%d")
            results.append(RuleResult(
                rule_id="ORO.FTL.210",
                title=title,
                ok=False,
                remark=(
                    f"{hm(total_td)} in the {days}-day window from {window_start} "
                    f"exceeds {hm(limit.value)}"
                ),
                binding_source=limit.source,
                subject=f"{days} days from {window_start}",
            ))
    return dedupe_overlapping(results)


@rule(level=Level.ROSTER, id="ORO.FTL.210(b)(2)",
      title="Maximum flight time in a calendar year")
def block_calendar_year(roster: Roster, ctx: Context) -> list[RuleResult]:
    """<= 900 h block in any calendar year."""
    limit = ctx.scheme.resolve("max_block_calendar_year")
    limit_h = limit.value.total_seconds() / 3600
    by_year: dict[int, float] = {}
    for d in roster.duties:
        by_year[d.report.year] = by_year.get(d.report.year, 0.0) + d.block_time.total_seconds() / 3600
    results = []
    for year, total_h in sorted(by_year.items()):
        if total_h > limit_h:
            results.append(RuleResult(
                rule_id="ORO.FTL.210(b)(2)",
                title="Maximum flight time in a calendar year",
                ok=False,
                remark=f"{hm(timedelta(hours=total_h))} block in {year} exceeds {hm(limit.value)}",
                binding_source=limit.source,
                subject=str(year),
            ))
    return results


@rule(level=Level.ROSTER, id="ORO.FTL.210(b)(3)",
      title="Maximum flight time in 12 consecutive months")
def block_12_months(roster: Roster, ctx: Context) -> list[RuleResult]:
    """<= 1000 h block in any 12 consecutive calendar months (month-aligned windows)."""
    from datetime import date
    limit = ctx.scheme.resolve("max_block_12_months")
    limit_h = limit.value.total_seconds() / 3600
    months = sorted({(d.report.year, d.report.month) for d in roster.duties})
    results = []
    seen: set[str] = set()
    for year, month in months:
        end_year = year + (month + 11) // 12
        end_month = (month + 11) % 12 + 1
        window_start = date(year, month, 1)
        window_end = date(end_year, end_month, 1)
        total_h = sum(
            d.block_time.total_seconds() / 3600
            for d in roster.duties
            if window_start <= date(d.report.year, d.report.month, 1) < window_end
        )
        key = f"{year}-{month:02d}"
        if total_h > limit_h and key not in seen:
            seen.add(key)
            results.append(RuleResult(
                rule_id="ORO.FTL.210(b)(3)",
                title="Maximum flight time in 12 consecutive months",
                ok=False,
                remark=f"{hm(timedelta(hours=total_h))} block in 12 months from {key} exceeds {hm(limit.value)}",
                binding_source=limit.source,
                subject=f"12 months from {key}",
            ))
    return results
