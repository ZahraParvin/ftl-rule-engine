"""Generate the test rosters, asserting the arithmetic as it goes.

The fixtures ARE the specification, so they must be exactly right. Hand-writing
timestamps invites a transcription error that silently makes a test meaningless;
this script computes them and asserts the property each fixture is meant to have.

Run from the repo root:  python tools/make_fixtures.py
"""
from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

TZ = "Europe/Oslo"
HOME = "ENGM"          # Oslo Gardermoen
AWAY = "ENBR"          # Bergen Flesland
OUT = Path(__file__).resolve().parent.parent / "tests" / "rosters"

PREP = timedelta(minutes=45)      # report -> first off-blocks
TURN = timedelta(minutes=40)      # on-blocks -> next off-blocks
POST = timedelta(minutes=30)      # on-blocks (last) -> release


def utc(local_str: str, tz: str = TZ) -> datetime:
    """'2026-09-01 06:00' local -> aware UTC datetime."""
    naive = datetime.strptime(local_str, "%Y-%m-%d %H:%M")
    return naive.replace(tzinfo=ZoneInfo(tz)).astimezone(timezone.utc)


def z(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def build_duty(report: datetime, sectors: int, fdp: timedelta,
               start: str = HOME, post: timedelta = POST) -> dict:
    """Lay out `sectors` legs so the FDP is exactly `fdp`."""
    flying = fdp - PREP - TURN * (sectors - 1)
    if flying <= timedelta(0):
        raise ValueError("fdp too short for that many sectors")
    per = flying / sectors
    airports = [start]
    for i in range(sectors):
        airports.append(AWAY if airports[-1] == HOME else HOME)

    legs = []
    t = report + PREP
    for i in range(sectors):
        off, on = t, t + per
        legs.append({
            "flight_no": f"DY{1000 + i}",
            "dep": airports[i], "arr": airports[i + 1],
            "off_block": z(off), "on_block": z(on),
        })
        t = on + TURN

    last_on = datetime.fromisoformat(legs[-1]["on_block"][:-1]).replace(tzinfo=timezone.utc)
    assert last_on - report == fdp, f"fdp mismatch: {last_on - report} != {fdp}"
    return {"report": z(report), "release": z(last_on + post), "legs": legs}


def roster(name: str, duties: list[dict], note: str) -> dict:
    return {"crew_id": "PARVIN_Z", "home_base": HOME, "base_tz": TZ,
            "_note": note, "duties": duties}


def write(name: str, data: dict) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / f"{name}.json").write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    print(f"  {name}.json  ({len(data['duties'])} duties)")


def duty_time(d: dict) -> timedelta:
    a = datetime.fromisoformat(d["report"][:-1])
    b = datetime.fromisoformat(d["release"][:-1])
    return b - a


def hm(td: timedelta) -> str:
    s = int(td.total_seconds())
    return f"{s // 3600}:{(s % 3600) // 60:02d}"


def main() -> None:
    print("writing fixtures:")

    # 1. 6 sectors from an 06:00 local report -> Table 2 limit 11:00, FDP 11:05.
    write("illegal_fdp_6_sectors", roster(
        "illegal_fdp_6_sectors",
        [build_duty(utc("2026-09-01 06:00"), 6, timedelta(hours=11, minutes=5))],
        "FDP 11:05 exceeds the 11:00 limit for 6 sectors reporting 06:00 local"))

    # 2. Late report, 16:30-16:59 band -> limit 11:15, FDP 11:20. Fails by 5 min.
    write("illegal_fdp_late_report", roster(
        "illegal_fdp_late_report",
        [build_duty(utc("2026-09-01 16:45"), 2, timedelta(hours=11, minutes=20))],
        "FDP 11:20 exceeds the 11:15 limit -- fails by five minutes"))

    # 3. 23:00 report falls in the 17:00-04:59 row, which wraps past midnight.
    write("illegal_fdp_wraparound", roster(
        "illegal_fdp_wraparound",
        [build_duty(utc("2026-09-01 23:00"), 4, timedelta(hours=10, minutes=15))],
        "23:00 report uses the wrapping 17:00-04:59 row; limit 10:00, FDP 10:15"))

    # 4. Rest at home base: 9:00 preceding duty, so the 12:00 floor binds.
    d1 = build_duty(utc("2026-09-01 06:00"), 2, timedelta(hours=8, minutes=30))
    assert duty_time(d1) == timedelta(hours=9), duty_time(d1)
    r1 = datetime.fromisoformat(d1["release"][:-1]).replace(tzinfo=timezone.utc)
    d2 = build_duty(r1 + timedelta(hours=11, minutes=30), 2, timedelta(hours=8))
    write("illegal_rest_home", roster(
        "illegal_rest_home", [d1, d2],
        "rest 11:30 after a 9:00 duty at home base -- the 12:00 floor binds"))

    # 5. Rest away from base: 11:00 preceding duty beats the 10:00 floor.
    d1 = build_duty(utc("2026-09-01 06:00"), 2, timedelta(hours=10, minutes=30))
    assert duty_time(d1) == timedelta(hours=11), duty_time(d1)
    r1 = datetime.fromisoformat(d1["release"][:-1]).replace(tzinfo=timezone.utc)
    d2 = build_duty(r1 + timedelta(hours=10, minutes=30), 2, timedelta(hours=8), start=AWAY)
    write("illegal_rest_away", roster(
        "illegal_rest_away", [d1, d2],
        "rest 10:30 away from base after an 11:00 duty -- the preceding duty binds, "
        "not the 10:00 floor"))

    # 6. Sliding 7-day window exceeds 60:00 while no calendar week does.
    #    Thu 3 Sep -> Wed 9 Sep 2026: 7 duties of 8:39.
    dt6 = timedelta(hours=8, minutes=39)
    duties, day = [], utc("2026-09-03 06:00")
    for i in range(7):
        duties.append(build_duty(day + timedelta(days=i), 2, dt6 - POST))
    total = sum((duty_time(d) for d in duties), timedelta())
    assert total > timedelta(hours=60), hm(total)
    weeks: dict[tuple, timedelta] = {}
    for d in duties:
        rep = datetime.fromisoformat(d["report"][:-1])
        weeks.setdefault(rep.isocalendar()[:2], timedelta())
        weeks[rep.isocalendar()[:2]] += duty_time(d)
    assert all(v <= timedelta(hours=60) for v in weeks.values()), \
        {k: hm(v) for k, v in weeks.items()}
    print(f"     sliding 7-day total {hm(total)}; calendar weeks "
          f"{[hm(v) for v in weeks.values()]}")
    write("illegal_rolling_7day", roster(
        "illegal_rolling_7day", duties,
        f"{hm(total)} in a sliding 7-day window; no calendar week exceeds 60:00"))

    # 7. More than 168 h between recurrent extended recovery rests.
    dt7 = timedelta(hours=7)
    duties, day = [], utc("2026-09-01 06:00")
    for i in range(8):
        duties.append(build_duty(day + timedelta(days=i), 2, dt7 - POST))
    first_report = datetime.fromisoformat(duties[0]["report"][:-1])
    last_release = datetime.fromisoformat(duties[-1]["release"][:-1])
    gap = last_release - first_report
    assert gap > timedelta(hours=168), hm(gap)
    week = sum((duty_time(d) for d in duties[:7]), timedelta())
    assert week < timedelta(hours=60), hm(week)   # isolate the RexRest rule
    print(f"     RexRest interval {hm(gap)}; worst 7-day duty total {hm(week)}")
    write("illegal_rexrest_gap", roster(
        "illegal_rexrest_gap", duties,
        f"{hm(gap)} between recovery rests, exceeding 168:00"))

    # 8. A 36 h wall-clock rest across the spring-forward change is only 35 h.
    d1 = build_duty(utc("2027-03-27 09:00"), 2, timedelta(hours=10, minutes=30))
    rel = datetime.fromisoformat(d1["release"][:-1]).replace(tzinfo=timezone.utc)
    assert rel.astimezone(ZoneInfo(TZ)).strftime("%H:%M") == "20:00", rel
    d2 = build_duty(utc("2027-03-29 08:00"), 2, timedelta(hours=8))
    rep2 = datetime.fromisoformat(d2["report"][:-1]).replace(tzinfo=timezone.utc)
    elapsed = rep2 - rel
    assert elapsed == timedelta(hours=35), hm(elapsed)
    print(f"     wall clock 20:00 Sat -> 08:00 Mon = 36:00, elapsed {hm(elapsed)}")
    write("illegal_rexrest_dst", roster(
        "illegal_rexrest_dst", [d1, d2],
        "36:00 of wall clock across the March clock change is 35:00 of actual "
        "rest -- short of the 36:00 minimum"))

    # 9. Legal, but within five minutes of several limits.
    specs = [
        ("2026-09-01 06:00", 6, timedelta(hours=10, minutes=55), "11:00"),
        (None,               3, timedelta(hours=11, minutes=55), "12:00"),
        (None,               2, timedelta(hours=12, minutes=55), "13:00"),
    ]
    duties, prev_release, prev_duty = [], None, None
    for i, (start, sectors, fdp, limit) in enumerate(specs):
        if start is not None:
            report = utc(start)
        else:
            rest = max(prev_duty, timedelta(hours=12)) + timedelta(minutes=5)
            report = prev_release + rest
        d = build_duty(report, sectors, fdp)
        duties.append(d)
        prev_release = datetime.fromisoformat(d["release"][:-1]).replace(tzinfo=timezone.utc)
        prev_duty = duty_time(d)
        loc = report.astimezone(ZoneInfo(TZ)).strftime("%H:%M")
        print(f"     duty {i}: report {loc} local, {sectors} sectors, "
              f"FDP {hm(fdp)} vs limit {limit}")
    total = sum((duty_time(d) for d in duties), timedelta())
    assert total < timedelta(hours=60), hm(total)
    write("legal_tight", roster(
        "legal_tight", duties,
        "every duty within five minutes of its Table 2 limit, every rest within "
        "five minutes of its floor -- all legal"))

    print("\nall fixture assertions passed")


if __name__ == "__main__":
    main()
