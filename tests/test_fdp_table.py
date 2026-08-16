"""ORO.FTL.205 Table 2 -- the lookup and its edge cases."""
from __future__ import annotations

from datetime import time, timedelta

import pytest

from conftest import fired
from ftl.tables import TABLE_2, lookup_unknown_acclimatisation
from ftl.timeutil import in_band, parse_clock, parse_hm


def test_table_shape_matches_sector_bands():
    for lo, hi, values in TABLE_2.rows:
        assert len(values) == len(TABLE_2.sector_bands), f"row {lo}-{hi} has {len(values)} values"


def test_every_row_is_monotonically_non_increasing():
    """More sectors can never allow a longer FDP."""
    for lo, hi, values in TABLE_2.rows:
        parsed = [parse_hm(v) for v in values]
        assert parsed == sorted(parsed, reverse=True), f"row {lo}-{hi} is not monotonic"


@pytest.mark.parametrize("sectors,index", [
    (1, 0), (2, 0), (3, 1), (4, 2), (5, 3), (6, 4), (7, 5), (8, 6), (9, 7),
    (10, 8), (14, 8),
])
def test_sector_index(sectors, index):
    assert TABLE_2.sector_index(sectors) == index


def test_sector_index_rejects_zero_sectors():
    with pytest.raises(ValueError):
        TABLE_2.sector_index(0)


@pytest.mark.parametrize("clock,expected", [
    ("23:00", True),    # inside the wrapping 17:00-04:59 row
    ("00:30", True),
    ("04:59", True),    # inclusive upper edge, next day
    ("17:00", True),    # inclusive lower edge
    ("05:00", False),   # just outside
    ("12:00", False),
])
def test_wraparound_band(clock, expected):
    """The 17:00-04:59 row wraps past midnight.

    A naive `lo <= t <= hi` matches nothing here, and the lookup then reports
    "no limit found" -- which reads like a pass and is worse than a wrong limit.
    """
    assert in_band(parse_clock(clock), parse_clock("17:00"), parse_clock("04:59")) is expected


@pytest.mark.parametrize("clock,sectors,expected", [
    ("06:00", 2, "13:00"),   # top-left of the table
    ("13:29", 2, "13:00"),   # last minute of the first band
    ("13:30", 3, "12:15"),
    ("16:45", 2, "11:15"),   # the five-minute fixture
    ("17:00", 1, "11:00"),
    ("23:00", 4, "10:00"),   # via the wrapping row
    ("03:00", 6, "09:00"),   # after midnight, still the wrapping row
    ("05:30", 3, "12:00"),   # early-morning bands are easy to get wrong
    ("05:59", 2, "12:45"),
    ("06:00", 10, "09:00"),  # 10+ sectors clamps to the last column
])
def test_lookup_known_values(clock, sectors, expected):
    assert TABLE_2.lookup(parse_clock(clock), sectors) == parse_hm(expected)


@pytest.mark.parametrize("sectors,expected", [
    (1, "11:00"), (2, "11:00"), (3, "10:30"), (4, "10:00"), (5, "09:30"),
    (6, "09:00"), (9, "09:00"),
])
def test_table_3_unknown_acclimatisation(sectors, expected):
    assert lookup_unknown_acclimatisation(sectors) == parse_hm(expected)


# --- rules over real rosters -------------------------------------------------

def test_six_sectors_over_limit_fires(check):
    assert fired(check("illegal_fdp_6_sectors"), "ORO.FTL.205(b)")


def test_late_report_fails_by_five_minutes(check):
    v = check("illegal_fdp_late_report")
    assert fired(v, "ORO.FTL.205(b)")
    remark = next(r.remark for r in v if r.rule_id == "ORO.FTL.205(b)")
    assert "11:20" in remark and "11:15" in remark, \
        f"the remark must name actual and limit, got: {remark!r}"


def test_wraparound_roster_fires(check):
    """A 23:00 report must resolve to the 17:00-04:59 row, not fall through."""
    assert fired(check("illegal_fdp_wraparound"), "ORO.FTL.205(b)")


def test_legal_tight_has_no_fdp_violation(check):
    """Five minutes under the limit is legal. An engine that rejects everything
    is not a legality checker."""
    assert not fired(check("legal_tight"), "ORO.FTL.205(b)")
