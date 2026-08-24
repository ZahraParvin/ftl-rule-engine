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

    Bands may wrap past midnight -- ORO.FTL.205 Table 2 has a 17:00-04:59 row.
    """
    if lo <= hi:
        return lo <= t <= hi
    # Wrapping band (e.g., 17:00-04:59): matches after lo OR before/at hi.
    return t >= lo or t <= hi


def local_nights_between(start: datetime, end: datetime, tz: str) -> int:
    """Count complete local nights (22:00-08:00) fully inside [start, end].

    Uses ZoneInfo so DST transitions are handled correctly -- a rest that spans
    the spring-forward clock change is shorter in UTC than its wall-clock span.
    """
    from datetime import date, timedelta as _td
    zone = ZoneInfo(tz)
    count = 0
    d = start.astimezone(zone).date()
    for _ in range(400):
        night_start = datetime(d.year, d.month, d.day, 22, 0, tzinfo=zone)
        next_day = d + _td(days=1)
        night_end = datetime(next_day.year, next_day.month, next_day.day, 8, 0, tzinfo=zone)
        if night_start > end:
            break
        if night_start >= start and night_end <= end:
            count += 1
        d = next_day
    return count


def encroaches_wocl(start: datetime, end: datetime, tz: str) -> timedelta:
    """How much of [start, end] falls inside the 02:00-05:59 local WOCL.

    Not needed for the Phase 1 rules, but ORO.FTL.205(d) extensions depend on it
    and it is cheap to have the hook in place.
    """
    raise NotImplementedError("encroaches_wocl: not required for Phase 1")


def local(dt: datetime, tz: str) -> datetime:
    return dt.astimezone(ZoneInfo(tz))
