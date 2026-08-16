"""Rule registry and evaluation.

Rules are declared, not called. Each one is named, carries its regulation
reference, states the level it evaluates at, and returns a result with a remark
a planner can act on. Adding a rule means writing a decorated function; it means
touching nothing else.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Callable, Iterable

from .limits import Scheme
from .model import Duty, Leg, Roster


class Level(Enum):
    LEG = auto()
    DUTY = auto()
    ROSTER = auto()   # rules needing sequence context: rest, cumulative windows


@dataclass(frozen=True)
class RuleResult:
    rule_id: str            # "ORO.FTL.205(b)" or a CBA clause
    title: str
    ok: bool
    remark: str = ""        # always populated on failure, with actual vs limit
    binding_source: str = ""
    subject: str = ""       # which duty or leg it fired on

    def __str__(self) -> str:
        mark = "✓" if self.ok else "✗"
        head = f"{mark} {self.rule_id}  {self.title}"
        if self.ok:
            return head
        lines = [head]
        if self.subject:
            lines.append(f"    {self.subject}")
        lines.append(f"    {self.remark}")
        if self.binding_source:
            lines.append(f"    Bound by: {self.binding_source}")
        return "\n".join(lines)


@dataclass
class Context:
    scheme: Scheme
    roster: Roster


@dataclass
class Rule:
    fn: Callable
    level: Level
    id: str
    title: str


RULES: list[Rule] = []


def rule(*, level: Level, id: str, title: str):
    """Register a rule. The decorated function returns RuleResult(s) or None."""
    def deco(fn):
        RULES.append(Rule(fn=fn, level=level, id=id, title=title))
        return fn
    return deco


def _as_list(x) -> list[RuleResult]:
    if x is None:
        return []
    if isinstance(x, RuleResult):
        return [x]
    return list(x)


def evaluate(roster: Roster, scheme: Scheme) -> list[RuleResult]:
    """Run every registered rule at its own level. Deterministic ordering."""
    import ftl.rules  # noqa: F401  -- import for side effect: rule registration

    ctx = Context(scheme=scheme, roster=roster)
    results: list[RuleResult] = []
    for r in sorted(RULES, key=lambda r: (r.level.value, r.id)):
        if r.level is Level.DUTY:
            for d in roster.duties:
                results += _as_list(r.fn(d, ctx))
        elif r.level is Level.LEG:
            for d in roster.duties:
                for leg in d.legs:
                    results += _as_list(r.fn(leg, ctx))
        else:
            results += _as_list(r.fn(roster, ctx))
    return results


def violations(results: Iterable[RuleResult]) -> list[RuleResult]:
    return [r for r in results if not r.ok]
