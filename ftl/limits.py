"""Layered limit resolution: regulation baseline + collective-agreement overlay.

The invariant that matters: a collective agreement may only *tighten* a
regulatory limit, never loosen it. Same reasoning as a privilege boundary -- a
layer below must not be able to widen what the layer above fixed.

When two airlines merge, this is the whole problem. Two agreements, one rule
system, and every limit has to resolve to the most restrictive of them while
still being able to tell a planner which document bound it.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta
from pathlib import Path

import yaml

from .timeutil import parse_hm


class SchemeError(ValueError):
    """Raised when an overlay tries to loosen a regulatory limit."""


@dataclass(frozen=True)
class Limit:
    value: timedelta
    source: str      # human-readable scheme name that bound this limit
    ref: str         # regulation article or CBA clause
    base_value: timedelta | None = None   # regulatory value, when overridden

    @property
    def was_tightened(self) -> bool:
        """True when an agreement overrode the regulatory value.

        Not `value < base_value`: tightening a MINIMUM means raising it. The
        direction check lives in _is_stricter and has already run by the time a
        Limit carries a base_value at all.
        """
        return self.base_value is not None and self.value != self.base_value


# Direction of each limit: "max" limits are tightened by lowering, "min" by raising.
LIMIT_DIRECTION: dict[str, str] = {
    "max_duty_7_days": "max",
    "max_duty_14_days": "max",
    "max_duty_28_days": "max",
    "max_block_28_days": "max",
    "max_block_calendar_year": "max",
    "max_block_12_months": "max",
    "min_rest_home_base": "min",
    "min_rest_away_base": "min",
    "rexrest_min_duration": "min",
    "rexrest_max_interval": "max",
}


@dataclass(frozen=True)
class Scheme:
    name: str
    limits: dict[str, tuple[timedelta, str]]           # key -> (value, ref)
    overrides: dict[str, tuple[timedelta, str]]        # key -> (value, ref)
    base_name: str = ""

    def resolve(self, key: str) -> Limit:
        """Most restrictive wins; remember which source bound it."""
        if key not in self.limits:
            raise KeyError(f"unknown limit {key!r}")
        base_value, base_ref = self.limits[key]
        if key not in self.overrides:
            return Limit(base_value, source=self.base_name or self.name, ref=base_ref)

        value, ref = self.overrides[key]
        if not _is_stricter(key, value, base_value):
            raise SchemeError(
                f"{self.name}: override of {key!r} to {value} is not stricter than "
                f"the regulatory {base_value} -- an agreement may only tighten a limit"
            )
        return Limit(value, source=self.name, ref=ref, base_value=base_value)


def _is_stricter(key: str, candidate: timedelta, base: timedelta) -> bool:
    direction = LIMIT_DIRECTION.get(key, "max")
    return candidate < base if direction == "max" else candidate > base


def load_scheme(name: str, schemes_dir: str | Path = "schemes") -> Scheme:
    """Load a scheme, following `extends` one level to the regulatory baseline."""
    schemes_dir = Path(schemes_dir)
    raw = yaml.safe_load((schemes_dir / f"{name}.yaml").read_text(encoding="utf-8"))

    if "extends" not in raw:
        return Scheme(
            name=raw["name"],
            limits={k: (parse_hm(v["value"]), v["ref"]) for k, v in raw["limits"].items()},
            overrides={},
            base_name=raw["name"],
        )

    base = load_scheme(raw["extends"], schemes_dir)
    return Scheme(
        name=raw["name"],
        limits=base.limits,
        overrides={
            k: (parse_hm(v["value"]), v["ref"]) for k, v in (raw.get("overrides") or {}).items()
        },
        base_name=base.name,
    )
