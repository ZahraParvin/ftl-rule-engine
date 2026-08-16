"""ORO.FTL.235 -- rest periods."""
from __future__ import annotations

from datetime import timedelta

from ..engine import Context, Level, RuleResult, rule
from ..model import Roster
from ..timeutil import hm, local_nights_between


@rule(level=Level.ROSTER, id="ORO.FTL.235(a)", title="Minimum rest at home base")
def min_rest_home_base(roster: Roster, ctx: Context) -> list[RuleResult]:
    """Rest before an FDP starting at home base: >= preceding duty, or 12 h.

    TODO(rule): for each duty after the first that starts at home base, compare
    roster.rest_before(i) against max(preceding duty_time, scheme floor).

    Note which of the two bound it -- the remark should say whether the floor or
    the preceding duty period was the binding term, because the fix differs.
    """
    raise NotImplementedError("min_rest_home_base")


@rule(level=Level.ROSTER, id="ORO.FTL.235(b)", title="Minimum rest away from home base")
def min_rest_away_base(roster: Roster, ctx: Context) -> list[RuleResult]:
    """Rest before an FDP starting away from base: >= preceding duty, or 10 h.

    TODO(rule): same shape as the home-base rule with a lower floor. The trap in
    the fixtures is a 11:00 preceding duty against a 10:30 rest -- the preceding
    duty binds, not the 10:00 floor.
    """
    raise NotImplementedError("min_rest_away_base")


@rule(level=Level.ROSTER, id="ORO.FTL.235(d)",
      title="Recurrent extended recovery rest")
def recurrent_extended_recovery_rest(roster: Roster, ctx: Context) -> list[RuleResult]:
    """>= 36 h including 2 local nights; <= 168 h between consecutive RexRests.

    TODO(rule): find the rest periods that qualify as a RexRest (duration and
    local_nights_between both satisfied), then check the interval between
    consecutive qualifying rests.

    Two failure modes, two remarks: a rest that nearly qualified but was short,
    and a gap that exceeded 168 h.

    Contract for short rosters: anchor the first interval at the start of the
    roster. A roster spanning less than the maximum interval cannot violate it,
    so tests/rosters/legal_tight.json (about 86 h) must come back clean.
    """
    raise NotImplementedError("recurrent_extended_recovery_rest")
