# ftl-rule-engine

A declarative rule engine that checks airline crew rosters against EASA Flight Time
Limitations — Regulation (EU) 965/2012, Annex III, Subpart FTL — with collective-agreement
overlays layered on top of the regulatory baseline.

Rules are declared, not called. Each one is named, carries its regulation reference, states the
level it evaluates at, and returns a remark a crew planner can act on.

> **Status: complete.** 72 tests, all green.

---

## RULES.rave — a study exercise, not production Rave

`RULES.rave` expresses the same eleven rules in the Jeppesen Rave rule language.

**It has never been compiled.** I have no access to a Jeppesen installation and the official
language reference is not public, so the syntax is reconstructed from published papers and public
teaching material. Treat it as a translation exercise that shows how these rules map onto Rave's
level model, traversers and table lookups — not as code that runs.

The Python in `ftl/` is the source of truth: every rule there has a passing test. Corrections from
anyone who writes Rave professionally are welcome.

---

## Rules

| Rule | Reference | Level | Implemented |
|---|---|---|:--:|
| Basic maximum daily FDP (Table 2) | ORO.FTL.205(b) | duty | ☑ |
| Maximum daily FDP, unknown acclimatisation (Table 3) | ORO.FTL.205(b)(2) | duty | n/a¹ |
| Maximum duty in 7 consecutive days | ORO.FTL.210(a)(1) | roster | ☑ |
| Maximum duty in 14 consecutive days | ORO.FTL.210(a)(2) | roster | ☑ |
| Maximum duty in 28 consecutive days | ORO.FTL.210(a)(3) | roster | ☑ |
| Maximum flight time in 28 consecutive days | ORO.FTL.210(b)(1) | roster | ☑ |
| Maximum flight time in a calendar year | ORO.FTL.210(b)(2) | roster | ☑ |
| Maximum flight time in 12 consecutive months | ORO.FTL.210(b)(3) | roster | ☑ |
| Minimum rest at home base | ORO.FTL.235(a) | roster | ☑ |
| Minimum rest away from home base | ORO.FTL.235(b) | roster | ☑ |
| Recurrent extended recovery rest | ORO.FTL.235(d) | roster | ☑ |

¹ The roster model treats every crew member as acclimatised, so Table 3 never applies. The hook is
in place and returns `None` rather than faking an acclimatisation state.

### Deliberately out of scope

Not partial implementations — omissions, and the reason for each:

- **Extensions without in-flight rest (205(d))** and **with in-flight rest (205(e))** — both depend
  on WOCL encroachment and crew augmentation, neither of which the roster model carries.
- **Commander's discretion (205(f))** — an operational decision recorded after the fact, not a
  planning-time constraint.
- **Split duty (220)**, **standby and reserve (225 / 230)** — need duty types the model does not have.
- **FRM (Table 4)** — only applies where an operator runs an approved fatigue risk management system.
- **Acclimatisation state machine (Table 1)** — time-zone-crossing state is a project of its own.

---

## The idea worth looking at

A collective agreement may only ever **tighten** a regulatory limit, never loosen it. The engine
resolves each limit to the most restrictive of the two and remembers which document bound it:

```yaml
# schemes/operator_a.yaml
extends: easa_base
name: "Operator A pilot CBA"
overrides:
  min_rest_home_base: {value: "14:00", ref: "CBA §7.2"}   # EASA floor is 12:00
  max_duty_7_days:    {value: "55:00", ref: "CBA §9.1"}   # EASA limit is 60:00
```

`schemes/operator_invalid.yaml` exists purely to prove the invariant — loading it raises
`SchemeError`, because an agreement that grants *less* rest than the regulation would otherwise
authorise an illegal roster. That is
[`test_an_agreement_cannot_loosen_a_regulatory_limit`](tests/test_scheme_overlay.py), and it is the
test to read first.

Note the direction handling: tightening a *maximum* means lowering it, tightening a *minimum* means
raising it. Getting that backwards is silent and dangerous, so `LIMIT_DIRECTION` makes it explicit.

The operator names are invented. No real airline's agreement terms appear in this repository.

---

## Report output

```
$ ftl check tests/rosters/illegal_rest_away.json --scheme operator_a

Roster PARVIN_Z  ·  scheme: Operator A pilot CBA (extends EASA base)
2 duties · 2026-09-01 → 2026-09-02

✗ ORO.FTL.235(b)  Minimum rest away from home base
    Duty 2 (2026-09-02, ENBR→ENGM)
    Rest 10:30 is less than the preceding duty period 11:00.
    Bound by: EASA base

1 violations · 10 rules passed
```

The `Bound by` line answers the question a planner always asks: *is this the law, or is this our
agreement?* Without it the report says a roster is illegal but not who to argue with.

---

## Test fixtures

The fixtures are the specification, so they are generated and self-checked rather than hand-written
— `tools/make_fixtures.py` asserts the property each roster is meant to have before writing it, and
CI fails if the checked-in JSON drifts.

| Fixture | What it proves |
|---|---|
| `illegal_fdp_6_sectors` | FDP 11:05 against an 11:00 limit, 6 sectors from an 06:00 local report |
| `illegal_fdp_late_report` | Fails by five minutes — 11:20 against 11:15 |
| `illegal_fdp_wraparound` | A 23:00 report resolves via the 17:00–04:59 row, which wraps past midnight |
| `illegal_rest_home` | 11:30 rest after a 9:00 duty — the 12:00 floor binds |
| `illegal_rest_away` | 10:30 rest after an 11:00 duty — the *preceding duty* binds, not the 10:00 floor |
| `illegal_rolling_7day` | 60:33 in a sliding 7-day window while no calendar week exceeds 60:00 |
| `illegal_rexrest_gap` | 175:00 between recovery rests, over the 168:00 maximum |
| `illegal_rexrest_dst` | 36:00 of wall clock across the spring-forward change is 35:00 of rest |
| `legal_tight` | Within five minutes of four limits and legal — proves no over-rejection |

`legal_tight` matters as much as the violations. An engine that rejects everything is not a legality
checker.

---

## Running it

```bash
pip install -e ".[dev]"
python tools/make_fixtures.py     # regenerate and re-assert the fixtures
pytest -q
ftl check tests/rosters/illegal_rest_away.json --scheme operator_a
```

Python 3.10+. Dependencies: polars (rolling windows), pyyaml (schemes). Standard-library `zoneinfo`
for all timezone arithmetic — never fixed UTC offsets, because `illegal_rexrest_dst` exists.

---

## Sources

Limits transcribed from the UK CAA regulatory library and cross-checked against the Norwegian CAA's
consolidated text:

- [ORO.FTL.205 Flight duty period](https://regulatorylibrary.caa.co.uk/965-2012/Content/Document%20Structure/03%20ORO/2%20Regs/05130_ORO.FTL.205_Flight_duty_period_FDP.htm)
- [ORO.FTL.210 Flight times and duty periods](https://regulatorylibrary.caa.co.uk/965-2012/Content/Document%20Structure/03%20ORO/2%20Regs/05140_ORO.FTL.210_Flight_times_and_duty_periods.htm)
- [ORO.FTL.235 Rest periods](https://regulatorylibrary.caa.co.uk/965-2012/Content/Regs/05190_ORO.FTL.235_Rest_periods.htm)
- [Regulation (EU) 965/2012 Annex III Part-ORO, FTL consolidated — Luftfartstilsynet](https://www.luftfartstilsynet.no/globalassets/dokumenter/regelverk/ftl-consolidated.pdf)

This is a personal project built to learn the domain. It is not affiliated with, derived from, or
equivalent to any commercial crew-management product.
