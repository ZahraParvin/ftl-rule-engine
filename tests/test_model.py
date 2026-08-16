"""The model itself -- mostly to pin down FDP vs duty period."""
from __future__ import annotations

from datetime import timedelta


def test_fdp_ends_at_on_blocks_not_at_release(load):
    """ORO.FTL.210(c): duty continues through post-flight duty; the FDP does not.

    Conflating the two is the most common beginner error in this domain.
    """
    duty = load("illegal_fdp_6_sectors").duties[0]
    assert duty.fdp == timedelta(hours=11, minutes=5)
    assert duty.duty_time == duty.fdp + timedelta(minutes=30)
    assert duty.duty_time > duty.fdp


def test_report_local_uses_the_reference_timezone(load):
    """Table 2 bands are local time, never UTC."""
    duty = load("illegal_fdp_6_sectors").duties[0]
    assert duty.report_local.strftime("%H:%M") == "06:00"
    assert duty.report.strftime("%H:%M") == "04:00"     # CEST is UTC+2 in September


def test_home_base_detection_selects_the_rest_rule(load):
    assert load("illegal_rest_home").duties[1].starts_at_home_base
    assert not load("illegal_rest_away").duties[1].starts_at_home_base


def test_rest_before_first_duty_is_none(load):
    roster = load("illegal_rest_home")
    assert roster.rest_before(0) is None
    assert roster.rest_before(1) == timedelta(hours=11, minutes=30)


def test_block_time_excludes_turnarounds(load):
    duty = load("illegal_fdp_6_sectors").duties[0]
    assert duty.block_time < duty.fdp
    assert duty.sectors == 6
