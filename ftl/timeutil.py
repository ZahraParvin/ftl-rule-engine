"""Time helpers. The DST-sensitive ones are deliberately left unimplemented."""
from __future__ import annotations

from datetime import datetime, time, timedelta
from zoneinfo import ZoneInfo

# ORO.FTL.105 definitions
WOCL_START = time(2, 0)    # window of circadian low, local
WOCL_END = time(5, 59)
NIGHT_START = time(22, 0)  # a "local night" is 22:00-08:00 local
NIGHT_END = time(8, 0)


def hm(td: timedelta) -> str:
    """Format a timedelta as H:MM, the way a crew planner reads it."""
    total = int(td.total_seconds())
    sign = "-" if total < 0 else ""
    total = abs(total)
    return f"{sign}{total // 3600}:{(total % 3600) // 60:02d}"


def parse_hm(s: str) -> timedelta:
    """'11:15' -> timedelta(hours=11, minutes=15). Hours may exceed 24."""
    h, m = s.split(":")
    return timedelta(hours=int(h), minutes=int(m))


def parse_clock(s: str) -> time:
    """'16:45' -> time(16, 45)."""
    h, m = s.split(":")
    return time(int(h), int(m))


def in_band(t: time, lo: time, hi: time) -> bool:
    """Is local clock time `t` inside the band [lo, hi], inclusive?

    TODO(rule): bands may wrap past midnight -- ORO.FTL.205 Table 2 has a
    17:00-04:59 row. A naive `lo <= t <= hi` silently matches nothing for a
    23:00 report and the table lookup then reports "no limit found", which is
    worse than a wrong limit because it looks like a pass.

    See tests/test_fdp_table.py::test_wraparound_band.
    """
    raise NotImplementedError("in_band: handle bands that wrap past midnight")


def local_nights_between(start: datetime, end: datetime, tz: str) -> int:
    """Count complete local nights inside a rest period.

    A local night is 22:00-08:00 local time in `tz`. ORO.FTL.235(d) requires a
    recurrent extended recovery rest to contain at least 2 of them.

    TODO(rule): use zoneinfo arithmetic, never fixed UTC offsets. A rest period
    spanning a DST transition changes elapsed length without changing wall-clock
    length -- see tests/test_rest.py::test_rexrest_short_across_spring_forward.
    """
    raise NotImplementedError("local_nights_between: count 22:00-08:00 local nights")


def encroaches_wocl(start: datetime, end: datetime, tz: str) -> timedelta:
    """How much of [start, end] falls inside the 02:00-05:59 local WOCL.

    Not needed for the Phase 1 rules, but ORO.FTL.205(d) extensions depend on it
    and it is cheap to have the hook in place.
    """
    raise NotImplementedError("encroaches_wocl: not required for Phase 1")


def local(dt: datetime, tz: str) -> datetime:
    return dt.astimezone(ZoneInfo(tz))
