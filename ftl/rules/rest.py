"""ORO.FTL.235 -- rest periods."""
from __future__ import annotations

from datetime import timedelta

from ..engine import Context, Level, RuleResult, rule
from ..model import Roster
from ..timeutil import hm, local_nights_between


def _min_rest_check(roster: Roster, ctx: Context, home: bool) -> list[RuleResult]:
    key = "min_rest_home_base" if home else "min_rest_away_base"
    rule_id = "ORO.FTL.235(a)" if home else "ORO.FTL.235(b)"
    title = "Minimum rest at home base" if home else "Minimum rest away from home base"
    floor_limit = ctx.scheme.resolve(key)
    results = []
    for i, duty in enumerate(roster.duties):
        if duty.starts_at_home_base != home:
            continue
        rest = roster.rest_before(i)
        if rest is None:
            continue
        preceding = roster.duties[i - 1]
        required = max(preceding.duty_time, floor_limit.value)
        if rest >= required:
            continue
        if preceding.duty_time >= floor_limit.value:
            binding_desc = f"{hm(preceding.duty_time)} preceding duty period"
        else:
            binding_desc = f"{hm(floor_limit.value)} regulatory floor"
        results.append(RuleResult(
            rule_id=rule_id,
            title=title,
            ok=False,
            remark=f"Rest {hm(rest)} is less than required {hm(required)} ({binding_desc})",
            binding_source=floor_limit.source,
            subject=f"Rest before {duty.report_local.strftime('%Y-%m-%d %H:%M')} local",
        ))
    return results


@rule(level=Level.ROSTER, id="ORO.FTL.235(a)", title="Minimum rest at home base")
def min_rest_home_base(roster: Roster, ctx: Context) -> list[RuleResult]:
    """Rest before an FDP starting at home base: >= preceding duty, or 12 h."""
    return _min_rest_check(roster, ctx, home=True)


@rule(level=Level.ROSTER, id="ORO.FTL.235(b)", title="Minimum rest away from home base")
def min_rest_away_base(roster: Roster, ctx: Context) -> list[RuleResult]:
    """Rest before an FDP starting away from base: >= preceding duty, or 10 h."""
    return _min_rest_check(roster, ctx, home=False)


@rule(level=Level.ROSTER, id="ORO.FTL.235(d)",
      title="Recurrent extended recovery rest")
def recurrent_extended_recovery_rest(roster: Roster, ctx: Context) -> list[RuleResult]:
    """>= 36 h including 2 local nights; <= 168 h between consecutive RexRests.

    Short rosters (span <= max interval) cannot violate the gap limit.
    """
    min_dur = ctx.scheme.resolve("rexrest_min_duration")
    max_interval = ctx.scheme.resolve("rexrest_max_interval")
    results = []
    qualifying_ends: list = []

    for i in range(1, len(roster.duties)):
        rest = roster.rest_before(i)
        if rest is None:
            continue
        rest_start = roster.duties[i - 1].release
        rest_end = roster.duties[i].report
        nights = local_nights_between(rest_start, rest_end, roster.duties[i].base_tz)
        if nights >= 2:
            if rest < min_dur.value:
                shortfall = min_dur.value - rest
                results.append(RuleResult(
                    rule_id="ORO.FTL.235(d)",
                    title="Recurrent extended recovery rest",
                    ok=False,
                    remark=(
                        f"Recovery rest {hm(rest)} contains {nights} local nights "
                        f"but is {hm(shortfall)} short of the {hm(min_dur.value)} minimum"
                    ),
                    binding_source=min_dur.source,
                    subject=f"Rest ending {rest_end.strftime('%Y-%m-%dT%H:%MZ')}",
                ))
            else:
                qualifying_ends.append(rest_end)

    if not qualifying_ends:
        roster_span = roster.duties[-1].release - roster.duties[0].report
        if roster_span > max_interval.value:
            results.append(RuleResult(
                rule_id="ORO.FTL.235(d)",
                title="Recurrent extended recovery rest",
                ok=False,
                remark=(
                    f"No extended recovery rest in {hm(roster_span)} "
                    f"(limit {hm(max_interval.value)})"
                ),
                binding_source=max_interval.source,
                subject=(
                    f"Roster {roster.duties[0].report.strftime('%Y-%m-%d')} "
                    f"to {roster.duties[-1].release.strftime('%Y-%m-%d')}"
                ),
            ))
    else:
        anchors = [roster.duties[0].report] + qualifying_ends
        for j in range(1, len(anchors)):
            gap = anchors[j] - anchors[j - 1]
            if gap > max_interval.value:
                results.append(RuleResult(
                    rule_id="ORO.FTL.235(d)",
                    title="Recurrent extended recovery rest",
                    ok=False,
                    remark=(
                        f"Gap between extended recovery rests {hm(gap)} "
                        f"exceeds {hm(max_interval.value)}"
                    ),
                    binding_source=max_interval.source,
                    subject=f"Gap ending {anchors[j].strftime('%Y-%m-%dT%H:%MZ')}",
                ))

    return results
