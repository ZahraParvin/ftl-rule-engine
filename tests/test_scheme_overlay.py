"""Layered schemes: a collective agreement may only tighten the regulation.

This is the file to point at in an interview. It is the invariant that makes
merging two airlines' agreements into one rule system safe.
"""
from __future__ import annotations

from datetime import timedelta

import pytest

from ftl.limits import SchemeError
from ftl.timeutil import parse_hm


def test_base_scheme_resolves_regulatory_values(scheme):
    s = scheme("easa_base")
    assert s.resolve("min_rest_home_base").value == parse_hm("12:00")
    assert s.resolve("max_duty_7_days").value == parse_hm("60:00")
    assert s.resolve("min_rest_home_base").source == "EASA base"


def test_overlay_tightens_and_reports_itself(scheme):
    s = scheme("operator_a")
    lim = s.resolve("min_rest_home_base")
    assert lim.value == parse_hm("14:00")
    assert lim.source == "Operator A pilot CBA"
    assert lim.ref == "CBA §7.2"
    assert lim.base_value == parse_hm("12:00")
    assert lim.was_tightened


def test_unoverridden_limits_fall_through_to_the_regulation(scheme):
    s = scheme("operator_a")
    lim = s.resolve("max_block_28_days")
    assert lim.value == parse_hm("100:00")
    assert lim.source == "EASA base"
    assert not lim.was_tightened


def test_two_agreements_tighten_different_limits(scheme):
    """The Widerøe-integration shape: one baseline, two overlays, no conflict."""
    a, b = scheme("operator_a"), scheme("operator_b")
    assert a.resolve("max_duty_7_days").value == parse_hm("55:00")
    assert b.resolve("max_duty_7_days").value == parse_hm("60:00")
    assert b.resolve("max_block_28_days").value == parse_hm("95:00")
    assert a.resolve("max_block_28_days").value == parse_hm("100:00")


def test_an_agreement_cannot_loosen_a_regulatory_limit(scheme):
    """A minimum rest of 10:00 is less than the regulation's 12:00 at home base.

    Silently accepting it would let a CBA authorise an illegal roster.
    """
    s = scheme("operator_invalid")
    with pytest.raises(SchemeError):
        s.resolve("min_rest_home_base")


def test_direction_is_respected_for_minimums_and_maximums(scheme):
    """Tightening means lowering a maximum and raising a minimum."""
    from ftl.limits import _is_stricter
    assert _is_stricter("max_duty_7_days", parse_hm("55:00"), parse_hm("60:00"))
    assert not _is_stricter("max_duty_7_days", parse_hm("65:00"), parse_hm("60:00"))
    assert _is_stricter("min_rest_home_base", parse_hm("14:00"), parse_hm("12:00"))
    assert not _is_stricter("min_rest_home_base", parse_hm("10:00"), parse_hm("12:00"))


def test_unknown_limit_key_raises(scheme):
    with pytest.raises(KeyError):
        scheme("easa_base").resolve("max_coffee_breaks")
