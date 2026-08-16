# ftl-rule-engine — design sketch

A declarative rule engine that checks crew rosters against EASA Flight Time Limitations
(Regulation (EU) 965/2012, Annex III, Subpart FTL), with stricter collective-agreement overlays.

**Why this exists:** to turn "I have watched RAVE tutorials" into "I have modelled flight time
limitations." The point is not to reimplement Jeppesen. The point is to show you understand what a
crew-legality rule system *is*: a declarative rule set, evaluated at defined levels over a roster,
producing remarks a planner can act on.

**Second, quieter purpose:** every technique in this project is one you have already shipped and
can defend under questioning. Nothing here requires you to learn a new stack. It re-runs your
existing track record inside the aviation domain, which is exactly the argument your CV and cover
letter already make.

---

## How this maps onto your CV

Build it so an interviewer reading your CV sees the same person twice.

| Already on your CV | Mirrored here |
|---|---|
| CHERI ISAv9 → C++ in gem5; conformance suite over encoding, privilege boundaries, exception paths | EASA Subpart FTL → Python rules; conformance suite over rule encoding, limit boundaries, wraparound and DST exception paths |
| TankLevel: written operating rules → ladder logic with thresholds, interlocks, alarms; **rung-level test bench, each rule in isolation** | Regulation text → declarative rules with limits and remarks; **rule-level test bench, each rule in isolation** |
| Thesis: FastAPI + PostgreSQL + Streamlit dashboard, Docker | Phase 2/3: FastAPI legality service, PostgreSQL violation store, Streamlit planner view, Docker Compose |
| Thesis: **12-phase integration suite, PASS 12/12** | **N-phase integration suite** over full-month rosters, reported the same way |
| Thesis: 102.2 FPS, 15.6 ms mean, 64.3 req/s — every claim quantified | Benchmark roster-checks/sec and p95 latency so this project also lands with a number |
| Montavis: pandas/**polars** batch pipelines over production data | polars `group_by_dynamic` for the rolling 7/14/28-day duty and block windows |
| Montavis: containerised deployment on Azure Container Apps | Same deployment path, already familiar |
| Skills: Git, **GitHub Actions CI** | CI running the rule suite on every push, badge in the README |
| Elevator: deterministic FSM, fault tolerance | Determinism test: same roster + same scheme → byte-identical report |

The rows that matter most for this job are the first two. CHERI proves you can implement a
specification; TankLevel proves you can encode written rules and test each one in isolation. This
project is the aviation-domain version of both, which is precisely the claim the cover letter makes.

---

## Four design decisions that make this look like RAVE, not generic Python

**1. Rules are declarative and registered.** In RAVE you write named rules that evaluate to
valid/invalid with a remark; you do not write `validate_roster()` with nested ifs. Use a rule
registry and a decorator. This is the same shape as your TankLevel rungs — independent rules, each
individually testable — so you already know why it is built this way.

**2. Rules evaluate at explicit levels.** RAVE evaluates at leg / duty / trip / roster level. Make
`Level` a first-class concept. This is the clearest single signal that you know the domain.

**3. Table 2 is a table, not an if-chain.** ORO.FTL.205(b) is literally a lookup table. Encode it
as data. RAVE has explicit table constructs for exactly this reason.

**4. Regulation and collective agreement are separate, layered rule sets.** A CBA may only be
*stricter* than the regulation. The engine resolves the binding limit and reports which source
bound it. This is the Widerøe-integration problem in miniature — two agreements, one rule system —
and it is the part worth talking about in the interview.

---

## Phasing — and when to apply

The application deadline is "snarest" with rolling review. **Apply after Phase 1.** Do not hold the
application waiting for a dashboard.

| Phase | Scope | Effort | Enough to mention? |
|---|---|---|---|
| **1 — Core engine** | model, engine, tables, 11 rules, rule-level tests, CLI | one weekend | **Yes. Apply here.** |
| **2 — Service + CI** | FastAPI endpoint, Docker, GitHub Actions, benchmark number | +1 day | Strengthens it |
| **3 — Persistence + view** | PostgreSQL violation store, Streamlit planner view, integration suite | +1–2 days | Only if you have time before the interview |

Phase 1 alone answers the question the interview will actually turn on. Phases 2 and 3 make it look
like your thesis, which is a good look but not the point.

---

## Layout

```
ftl-rule-engine/
  ftl/
    model.py          # Leg, Duty, Trip, Roster
    timeutil.py       # local time, WOCL, local night, DST-safe helpers
    tables.py         # ORO.FTL.205 Tables 2 and 3 as data
    engine.py         # Level, rule registry, evaluation, RuleResult
    limits.py         # layered limit resolution (regulation + CBA overlay)
    windows.py        # polars rolling windows for cumulative rules
    rules/
      fdp.py          # ORO.FTL.205
      cumulative.py   # ORO.FTL.210
      rest.py         # ORO.FTL.235
    cli.py            # ftl check roster.json --scheme operator_a
    api.py            # Phase 2: FastAPI
  schemes/
    easa_base.yaml
    operator_a.yaml   # invented CBA overlay
    operator_b.yaml   # invented CBA overlay, different shape
  tests/
    test_fdp_table.py
    test_rest.py
    test_cumulative.py
    test_scheme_overlay.py
    test_determinism.py
    rosters/          # legal_*.json and illegal_*.json fixtures
  README.md
```

Use invented operator names in the CBA overlays. Do not present guessed Norwegian or Widerøe
agreement terms as real — you do not have them, and an interviewer from that company would know
immediately.

---

## Data model

```python
@dataclass(frozen=True)
class Leg:
    flight_no: str
    dep: str                  # ICAO
    arr: str
    off_block: datetime       # UTC
    on_block: datetime        # UTC

@dataclass(frozen=True)
class Duty:
    report: datetime          # UTC
    release: datetime         # UTC
    legs: tuple[Leg, ...]
    home_base: str
    base_tz: str              # IANA, e.g. "Europe/Oslo"

    @property
    def sectors(self) -> int:
        return len(self.legs)

    @property
    def fdp(self) -> timedelta:
        """FDP runs from report to on-blocks of the final sector."""
        return self.legs[-1].on_block - self.report

    @property
    def duty_time(self) -> timedelta:
        """Duty includes post-flight duty; runs report to release."""
        return self.release - self.report

    @property
    def block_time(self) -> timedelta:
        return sum((l.on_block - l.off_block for l in self.legs), timedelta())

@dataclass(frozen=True)
class Roster:
    crew_id: str
    duties: tuple[Duty, ...]  # chronological
```

**Note the FDP / duty distinction.** FDP ends at on-blocks of the last sector; duty continues
through post-flight duties (ORO.FTL.210(c)). Conflating them is the most common beginner error in
this domain. Getting it right with a test that proves it is worth a sentence in your README.

---

## The engine

```python
class Level(Enum):
    LEG = auto()
    DUTY = auto()
    ROSTER = auto()          # rules needing sequence context (rest, cumulative)

@dataclass
class RuleResult:
    rule_id: str             # "ORO.FTL.205(b)"
    title: str
    ok: bool
    remark: str = ""         # planner-readable, always populated on failure
    binding_source: str = "" # "EASA" | "OPERATOR_A_CBA" — which limit bound
    subject: str = ""        # which duty/leg it fired on

RULES: list[Rule] = []

def rule(*, level: Level, id: str, title: str):
    def deco(fn):
        RULES.append(Rule(fn=fn, level=level, id=id, title=title))
        return fn
    return deco

def evaluate(roster: Roster, scheme: Scheme) -> list[RuleResult]:
    results = []
    ctx = Context(scheme=scheme, roster=roster)
    for r in RULES:
        if r.level is Level.DUTY:
            results += [r.fn(d, ctx) for d in roster.duties]
        elif r.level is Level.LEG:
            results += [r.fn(l, ctx) for d in roster.duties for l in d.legs]
        else:
            results += r.fn(roster, ctx)
    return [x for x in results if x is not None]
```

Every failing result carries a remark naming the actual and the limit. "FDP violation" is useless
to a planner. `FDP 11:20 exceeds 11:15 (EASA Table 2, 2 sectors, report 16:45 local)` is what they
need — the same instinct as your TankLevel alarm design, where the alarm has to say which threshold
tripped.

---

## Table 2 as data

Values from ORO.FTL.205(b) Table 2 — maximum daily FDP, acclimatised crew. Copy exactly; a
transcription error here undermines the whole project.

```python
# Columns: 1-2, 3, 4, 5, 6, 7, 8, 9, 10+ sectors
TABLE_2 = FdpTable(
    ref="ORO.FTL.205(b) Table 2",
    sector_bands=[(1, 2), (3, 3), (4, 4), (5, 5), (6, 6),
                  (7, 7), (8, 8), (9, 9), (10, None)],
    rows=[
        ("06:00", "13:29", ["13:00","12:30","12:00","11:30","11:00","10:30","10:00","09:30","09:00"]),
        ("13:30", "13:59", ["12:45","12:15","11:45","11:15","10:45","10:15","09:45","09:15","09:00"]),
        ("14:00", "14:29", ["12:30","12:00","11:30","11:00","10:30","10:00","09:30","09:00","09:00"]),
        ("14:30", "14:59", ["12:15","11:45","11:15","10:45","10:15","09:45","09:15","09:00","09:00"]),
        ("15:00", "15:29", ["12:00","11:30","11:00","10:30","10:00","09:30","09:00","09:00","09:00"]),
        ("15:30", "15:59", ["11:45","11:15","10:45","10:15","09:45","09:15","09:00","09:00","09:00"]),
        ("16:00", "16:29", ["11:30","11:00","10:30","10:00","09:30","09:00","09:00","09:00","09:00"]),
        ("16:30", "16:59", ["11:15","10:45","10:15","09:45","09:15","09:00","09:00","09:00","09:00"]),
        ("17:00", "04:59", ["11:00","10:30","10:00","09:30","09:00","09:00","09:00","09:00","09:00"]),
        ("05:00", "05:14", ["12:00","11:30","11:00","10:30","10:00","09:30","09:00","09:00","09:00"]),
        ("05:15", "05:29", ["12:15","11:45","11:15","10:45","10:15","09:45","09:15","09:00","09:00"]),
        ("05:30", "05:44", ["12:30","12:00","11:30","11:00","10:30","10:00","09:30","09:00","09:00"]),
        ("05:45", "05:59", ["12:45","12:15","11:45","11:15","10:45","10:15","09:45","09:15","09:00"]),
    ],
)
```

**Two traps worth a test each:**

- The `17:00–04:59` row **wraps past midnight**. A naive `lo <= t <= hi` silently matches nothing
  for a 23:00 report and the engine returns "no limit found". Handle wraparound explicitly.
- The bands are **local time at the reference point**, not UTC and not the departure airport. Store
  the base timezone on the duty and convert.

Table 3 (unknown acclimatisation) is a flat one-row lookup by sector count — five lines, and it
shows you read past the first table.

---

## The rules to implement

| Rule | Reference | What it checks |
|---|---|---|
| Basic max daily FDP | ORO.FTL.205(b) | FDP ≤ Table 2 value for report time + sector count |
| Max daily FDP, unknown acclimatisation | ORO.FTL.205(b)(2) | FDP ≤ Table 3 value |
| Duty in 7 days | ORO.FTL.210(a)(1) | ≤ 60 h in any 7 consecutive days |
| Duty in 14 days | ORO.FTL.210(a)(2) | ≤ 110 h in any 14 consecutive days |
| Duty in 28 days | ORO.FTL.210(a)(3) | ≤ 190 h in any 28 consecutive days |
| Block in 28 days | ORO.FTL.210(b)(1) | ≤ 100 h flight time in any 28 consecutive days |
| Block in calendar year | ORO.FTL.210(b)(2) | ≤ 900 h |
| Block in 12 months | ORO.FTL.210(b)(3) | ≤ 1000 h in any 12 consecutive calendar months |
| Minimum rest at home base | ORO.FTL.235(a) | ≥ preceding duty period, or 12 h, whichever greater |
| Minimum rest away from base | ORO.FTL.235(b) | ≥ preceding duty period, or 10 h, whichever greater |
| Recurrent extended recovery rest | ORO.FTL.235(d) | ≥ 36 h including 2 local nights; ≤ 168 h between consecutive RexRests |

Eleven rules. Plenty. Resist adding more.

**Explicitly out of scope — say so in the README.** Extensions without in-flight rest (205(d)),
extensions with in-flight rest (205(e)), commander's discretion (205(f)), split duty (220), standby
and reserve (225/230), FRM (Table 4), and the full acclimatisation state machine for time-zone
crossings (Table 1). Listing what you deliberately left out, and why, is a stronger signal than
quietly implementing half of it — the same instinct as scoping your thesis validation to 12 defined
phases rather than claiming coverage you did not have.

---

## The two rules where the bugs live

**Rolling windows — use polars.** "Any 7 consecutive days" is a sliding window anchored anywhere,
not a calendar week. A roster can have no calendar week over 60 hours and still be illegal. This is
the same rolling-aggregation shape as the Montavis batch pipelines, so use the tool you already
know:

```python
import polars as pl

def rolling_duty_hours(roster: Roster, days: int) -> pl.DataFrame:
    df = pl.DataFrame({
        "report":  [d.report for d in roster.duties],
        "duty_h":  [d.duty_time.total_seconds() / 3600 for d in roster.duties],
        "block_h": [d.block_time.total_seconds() / 3600 for d in roster.duties],
    }).sort("report")

    return df.rolling(index_column="report", period=f"{days}d", closed="left").agg(
        pl.col("duty_h").sum().alias("duty_window"),
        pl.col("block_h").sum().alias("block_window"),
    )
```

Anchoring on each duty start is sufficient — the worst window always begins at a duty. Dedupe
overlapping reports so a planner sees one violation, not forty. Note `closed="left"` matters:
"any 7 consecutive days" is a half-open interval and getting it closed on both ends double-counts a
duty landing exactly on the boundary. Write the test.

**Local nights and DST.** A local night is 22:00–08:00 local *where the rest is taken*, and RexRest
needs 36 hours containing two of them. Rest spanning a DST change is the classic failure. Use
`zoneinfo`, never fixed offsets, and test a rest period running across the last Sunday in October.

---

## Layered schemes — the part worth talking about

```yaml
# schemes/operator_a.yaml
extends: easa_base
name: "Operator A pilot CBA"
overrides:
  min_rest_home_base:
    floor: "14:00"        # stricter than the EASA 12:00 floor
    ref: "CBA §7.2"
  max_duty_7_days:
    limit: "55:00"        # stricter than 60:00
    ref: "CBA §9.1"
```

```python
def resolve(self, key: str) -> Limit:
    """Most restrictive wins; remember which source bound it."""
    reg = self.base[key]
    cba = self.overrides.get(key)
    if cba is None or not cba.is_stricter_than(reg):
        return Limit(reg.value, source=self.base.name, ref=reg.ref)
    return Limit(cba.value, source=self.name, ref=cba.ref)
```

Then assert that a CBA can never *loosen* a regulatory limit — an overlay attempting
`min_rest_home_base: 10:00` either raises or is ignored. That test is the whole argument: it is the
invariant that makes merging two airlines' agreements into one rule system safe, and it is what you
would be doing at Norwegian.

This is the same reasoning as the CHERI privilege-boundary tests — a lower-privilege layer must
never be able to widen a limit set by the layer above it. Say that in the interview.

---

## Test fixtures — build the illegal rosters first

Write the violations before the engine. They are the specification. This is the TankLevel rung-level
approach: one rule, one isolated test, one expected trip.

| Fixture | Should fire |
|---|---|
| `illegal_fdp_6_sectors.json` | Report 06:00 local, 6 sectors, FDP 11:05 → limit 11:00 |
| `illegal_fdp_late_report.json` | Report 16:45, 2 sectors, FDP 11:20 → limit 11:15, fails by 5 min |
| `illegal_fdp_wraparound.json` | Report 23:00, 4 sectors, FDP 10:15 → limit 10:00 via the 17:00–04:59 row |
| `illegal_rest_home.json` | 9 h duty, 11:30 rest at base → 12:00 floor binds |
| `illegal_rest_away.json` | 11 h duty, 10:30 rest away → preceding duty binds, not the 10:00 floor |
| `illegal_rolling_7day.json` | 60:30 in a sliding 7-day window, no calendar week over 60 |
| `illegal_rexrest_gap.json` | 170 h between recovery rests → exceeds 168 |
| `illegal_dst_night.json` | RexRest across the October clock change, short by one local night |
| `legal_tight.json` | Within 5 minutes of four different limits, all legal — proves no over-rejection |

`legal_tight.json` matters as much as the violations. An engine that rejects everything is not a
legality checker, and a hiring manager will ask.

Add `test_determinism.py`: same roster + same scheme → byte-identical report across runs. Cheap, and
it echoes the deterministic-FSM work already on your CV.

---

## CLI output

Make it look like a legality report, because that is what it is.

```
$ ftl check rosters/illegal_rest_away.json --scheme operator_a

Roster PARVIN_Z  ·  scheme: Operator A pilot CBA (extends EASA base)
14 duties · 2026-09-01 → 2026-09-28

✗ ORO.FTL.235(b)  Minimum rest away from home base
    Duty 7 (2026-09-14, BGO→TRD→BGO)
    Rest 10:30 is less than the preceding duty period 11:00.
    Bound by: EASA base

✗ CBA §9.1  Maximum duty in 7 consecutive days
    56:15 in the 7 days from 2026-09-08 exceeds 55:00.
    Bound by: Operator A pilot CBA (EASA base allows 60:00)

2 violations · 9 rules passed
```

The "Bound by" line is what will get remembered. It answers the question a crew planner always asks:
*is this the law, or is this our agreement?*

---

## Phase 2 — service, CI, and a number

Straight reuse of your thesis stack. Keep it thin.

```python
# ftl/api.py
app = FastAPI(title="FTL legality service")

@app.post("/check", response_model=LegalityReport)
def check(roster: RosterIn, scheme: str = "easa_base") -> LegalityReport:
    results = evaluate(roster.to_domain(), load_scheme(scheme))
    return LegalityReport.from_results(results)
```

Docker Compose, GitHub Actions running the rule suite on push, and one benchmark:

```
$ ftl bench --rosters 1000 --duties-per-roster 28
1000 rosters (28 duties each) checked in 4.1 s — 244 rosters/s, p95 18.2 ms
```

Get a real number. Your CV quantifies every claim; this project should too, or it will read as the
one soft bullet on an otherwise hard document.

**Phase 3, only if time allows:** PostgreSQL table of violations keyed by crew and scheme, a
Streamlit page showing a month grid with violations highlighted, and an integration suite reported
as `PASS n / FAIL 0` in the README — the same format as your thesis.

---

## One thing to skip

You could point an LLM at the regulation text to generate rule stubs, and it would work. Leave it
out of this project. In a safety-critical legality context it reads as unserious, and it invites the
one question you do not want: "so did you actually read the regulation?" Keep RAGCore as the
separate LLM artifact it already is.

---

## README — write it for the hiring manager

Lead with the rule table: every rule, its regulation reference, implemented yes/no. Then the
layered-scheme idea in one paragraph. Then the out-of-scope list. Then how to run the tests, and the
benchmark number.

Do not write "inspired by RAVE" or claim RAVE equivalence. Write what it is: a declarative FTL rule
engine built to learn the domain.

---

## How to use this in the application

CV, under Selected Projects — matched to the quantified style of your other bullets:

> **FTL Rule Engine — Declarative Crew Legality Checking** · Personal Project · 2026
> Python engine evaluating crew rosters against EASA Subpart FTL (ORO.FTL.205 / 210 / 235):
> table-driven maximum daily FDP, polars rolling duty and block-time windows, rest and recovery
> rules, with collective-agreement overlays layered over the regulatory baseline and a
> most-restrictive-wins resolver that reports which source bound each limit. Rule-level test suite
> with deliberately illegal rosters covering wraparound, DST and sliding-window edge cases;
> FastAPI service, Docker, GitHub Actions CI.

If you build Phase 1 only, cut the last clause and the word "polars" stays.

Cover letter, in the paragraph where you name the RAVE gap:

> To make the self-study concrete I built a declarative rule engine over EASA Subpart FTL —
> table-driven FDP limits, rolling duty windows, rest rules, and collective-agreement overlays that
> can only tighten the regulatory baseline. Happy to walk through it.

The ninety-second answer to "you have not used RAVE in production, why should we train you?" is:
the CHERI specification work, then this — and the through-line is that both are the same job.

---

## Sources

- [ORO.FTL.205 Flight duty period (FDP) — UK CAA regulatory library](https://regulatorylibrary.caa.co.uk/965-2012/Content/Document%20Structure/03%20ORO/2%20Regs/05130_ORO.FTL.205_Flight_duty_period_FDP.htm)
- [ORO.FTL.210 Flight times and duty periods — UK CAA regulatory library](https://regulatorylibrary.caa.co.uk/965-2012/Content/Document%20Structure/03%20ORO/2%20Regs/05140_ORO.FTL.210_Flight_times_and_duty_periods.htm)
- [ORO.FTL.235 Rest periods — UK CAA regulatory library](https://regulatorylibrary.caa.co.uk/965-2012/Content/Regs/05190_ORO.FTL.235_Rest_periods.htm)
- [Regulation (EU) 965/2012 Annex III Part-ORO, FTL consolidated — Luftfartstilsynet](https://www.luftfartstilsynet.no/globalassets/dokumenter/regelverk/ftl-consolidated.pdf)

Verify Table 2 against the consolidated PDF before you commit it. Transcribing a regulatory table by
hand is exactly the error this project is meant to prove you do not make.
