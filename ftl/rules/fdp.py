"""ORO.FTL.205 -- flight duty period."""
from __future__ import annotations

from ..engine import Context, Level, RuleResult, rule
from ..model import Duty
from ..tables import TABLE_2, lookup_unknown_acclimatisation
from ..timeutil import hm


@rule(level=Level.DUTY, id="ORO.FTL.205(b)", title="Basic maximum daily FDP")
def max_daily_fdp(duty: Duty, ctx: Context) -> RuleResult:
    """FDP must not exceed the Table 2 value for report time and sector count."""
    limit = TABLE_2.lookup(duty.report_local.time(), duty.sectors)
    ok = duty.fdp <= limit
    sector_word = "sector" if duty.sectors == 1 else "sectors"
    remark = (
        f"FDP {hm(duty.fdp)} exceeds {hm(limit)} "
        f"(ORO.FTL.205(b) Table 2, {duty.sectors} {sector_word}, "
        f"report {duty.report_local.strftime('%H:%M')} local)"
    ) if not ok else ""
    return RuleResult(
        rule_id="ORO.FTL.205(b)",
        title="Basic maximum daily FDP",
        ok=ok,
        remark=remark,
        subject=f"Duty {duty.report_local.strftime('%Y-%m-%d %H:%M')} local",
    )


@rule(level=Level.DUTY, id="ORO.FTL.205(b)(2)",
      title="Maximum daily FDP -- unknown acclimatisation")
def max_daily_fdp_unknown(duty: Duty, ctx: Context) -> RuleResult | None:
    """Table 3 applies when the crew member's acclimatisation state is unknown.

    TODO(rule): Phase 1 treats every crew member as acclimatised, so this rule
    should return None until the roster model carries an acclimatisation state.
    Leave the hook; do not fake the state.
    """
    return None
