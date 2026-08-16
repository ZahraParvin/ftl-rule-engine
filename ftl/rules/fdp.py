"""ORO.FTL.205 -- flight duty period."""
from __future__ import annotations

from ..engine import Context, Level, RuleResult, rule
from ..model import Duty
from ..tables import TABLE_2, lookup_unknown_acclimatisation
from ..timeutil import hm


@rule(level=Level.DUTY, id="ORO.FTL.205(b)", title="Basic maximum daily FDP")
def max_daily_fdp(duty: Duty, ctx: Context) -> RuleResult:
    """FDP must not exceed the Table 2 value for report time and sector count.

    TODO(rule): look up the limit with TABLE_2.lookup(duty.report_local.time(),
    duty.sectors), compare against duty.fdp, and on failure build a remark that
    names the actual, the limit, the sector count and the LOCAL report time.

    "FDP violation" is useless to a planner. This is what they need:
        FDP 11:20 exceeds 11:15 (ORO.FTL.205(b) Table 2, 2 sectors,
        report 16:45 local)
    """
    raise NotImplementedError("max_daily_fdp")


@rule(level=Level.DUTY, id="ORO.FTL.205(b)(2)",
      title="Maximum daily FDP -- unknown acclimatisation")
def max_daily_fdp_unknown(duty: Duty, ctx: Context) -> RuleResult | None:
    """Table 3 applies when the crew member's acclimatisation state is unknown.

    TODO(rule): Phase 1 treats every crew member as acclimatised, so this rule
    should return None until the roster model carries an acclimatisation state.
    Leave the hook; do not fake the state.
    """
    return None
