"""ORO.FTL.205 maximum daily FDP tables, encoded as data.

These are lookup tables in the regulation, so they are lookup tables here. An
if-chain would work and would be the wrong shape: RAVE models this kind of limit
with an explicit table construct, and so does every crew system built on it.

Values transcribed from ORO.FTL.205(b), Regulation (EU) 965/2012 Annex III.
Verify against the consolidated PDF before trusting them.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import time, timedelta

from .timeutil import in_band, parse_clock, parse_hm

SECTOR_BANDS: list[tuple[int, int | None]] = [
    (1, 2), (3, 3), (4, 4), (5, 5), (6, 6), (7, 7), (8, 8), (9, 9), (10, None),
]


@dataclass(frozen=True)
class FdpTable:
    ref: str
    sector_bands: list[tuple[int, int | None]]
    rows: list[tuple[str, str, list[str]]]   # (band_lo, band_hi, per-sector limits)

    def sector_index(self, sectors: int) -> int:
        if sectors < 1:
            raise ValueError("a duty with no sectors has no FDP limit")
        for i, (lo, hi) in enumerate(self.sector_bands):
            if sectors >= lo and (hi is None or sectors <= hi):
                return i
        raise ValueError(f"no sector band for {sectors} sectors")

    def lookup(self, report_local: time, sectors: int) -> timedelta:
        """Maximum daily FDP for this local report time and sector count."""
        col = self.sector_index(sectors)
        for lo_str, hi_str, values in self.rows:
            if in_band(report_local, parse_clock(lo_str), parse_clock(hi_str)):
                return parse_hm(values[col])
        raise ValueError(f"{self.ref}: no row matches report time {report_local}")


# Table 2 -- acclimatised crew members. Columns: 1-2, 3, 4, 5, 6, 7, 8, 9, 10+
TABLE_2 = FdpTable(
    ref="ORO.FTL.205(b) Table 2",
    sector_bands=SECTOR_BANDS,
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

# Table 3 -- crew in an unknown state of acclimatisation. Flat, sectors only.
TABLE_3_UNKNOWN: list[tuple[tuple[int, int | None], str]] = [
    ((1, 2), "11:00"), ((3, 3), "10:30"), ((4, 4), "10:00"),
    ((5, 5), "09:30"), ((6, None), "09:00"),
]


def lookup_unknown_acclimatisation(sectors: int) -> timedelta:
    for (lo, hi), value in TABLE_3_UNKNOWN:
        if sectors >= lo and (hi is None or sectors <= hi):
            return parse_hm(value)
    raise ValueError(f"no Table 3 entry for {sectors} sectors")
