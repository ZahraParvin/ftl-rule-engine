"""Domain model: Leg, Duty, Roster.

Deliberately small. Everything the rules need is derived from these three types.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo


def _parse(ts: str) -> datetime:
    """Parse an ISO-8601 UTC timestamp ending in 'Z'."""
    if not ts.endswith("Z"):
        raise ValueError(f"timestamps must be UTC and end in 'Z': {ts!r}")
    return datetime.fromisoformat(ts[:-1]).replace(tzinfo=timezone.utc)


@dataclass(frozen=True)
class Leg:
    flight_no: str
    dep: str            # ICAO
    arr: str            # ICAO
    off_block: datetime  # UTC
    on_block: datetime   # UTC

    @property
    def block_time(self) -> timedelta:
        return self.on_block - self.off_block


@dataclass(frozen=True)
class Duty:
    report: datetime      # UTC
    release: datetime     # UTC
    legs: tuple[Leg, ...]
    home_base: str        # ICAO of the crew member's home base
    base_tz: str          # IANA zone of the reference point, e.g. "Europe/Oslo"

    @property
    def sectors(self) -> int:
        return len(self.legs)

    @property
    def fdp(self) -> timedelta:
        """Flight duty period: report until on-blocks of the final sector.

        Not the same as duty_time. ORO.FTL.210(c) keeps the duty period running
        through post-flight duties; the FDP has already ended.
        """
        return self.legs[-1].on_block - self.report

    @property
    def duty_time(self) -> timedelta:
        """Duty period: report until release, including post-flight duty."""
        return self.release - self.report

    @property
    def block_time(self) -> timedelta:
        return sum((leg.block_time for leg in self.legs), timedelta())

    @property
    def report_local(self) -> datetime:
        """Report time in local time at the reference point.

        Table 2 bands are local, never UTC and never the departure airport.
        """
        return self.report.astimezone(ZoneInfo(self.base_tz))

    @property
    def starts_at_home_base(self) -> bool:
        """True when the FDP starts at home base -- selects the rest rule."""
        return self.legs[0].dep == self.home_base


@dataclass(frozen=True)
class Roster:
    crew_id: str
    duties: tuple[Duty, ...]   # chronological, ascending by report

    @classmethod
    def from_json(cls, path: str | Path) -> "Roster":
        raw = json.loads(Path(path).read_text(encoding="utf-8"))
        home_base = raw["home_base"]
        base_tz = raw["base_tz"]
        duties = tuple(
            Duty(
                report=_parse(d["report"]),
                release=_parse(d["release"]),
                legs=tuple(
                    Leg(
                        flight_no=l["flight_no"],
                        dep=l["dep"],
                        arr=l["arr"],
                        off_block=_parse(l["off_block"]),
                        on_block=_parse(l["on_block"]),
                    )
                    for l in d["legs"]
                ),
                home_base=home_base,
                base_tz=base_tz,
            )
            for d in raw["duties"]
        )
        duties = tuple(sorted(duties, key=lambda d: d.report))
        return cls(crew_id=raw["crew_id"], duties=duties)

    def rest_before(self, index: int) -> timedelta | None:
        """Rest period preceding duty `index`, or None for the first duty."""
        if index == 0:
            return None
        return self.duties[index].report - self.duties[index - 1].release
