"""ftl check <roster.json> --scheme <name>

Prints a legality report. The "Bound by" line answers the question a crew planner
always asks: is this the law, or is this our agreement?
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .engine import evaluate, violations
from .limits import load_scheme
from .model import Roster


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="ftl")
    sub = p.add_subparsers(dest="cmd", required=True)

    chk = sub.add_parser("check", help="check a roster for legality")
    chk.add_argument("roster", type=Path)
    chk.add_argument("--scheme", default="easa_base")
    chk.add_argument("--schemes-dir", type=Path, default=Path("schemes"))

    args = p.parse_args(argv)

    roster = Roster.from_json(args.roster)
    scheme = load_scheme(args.scheme, args.schemes_dir)
    results = evaluate(roster, scheme)
    bad = violations(results)

    span = f"{roster.duties[0].report:%Y-%m-%d} → {roster.duties[-1].release:%Y-%m-%d}"
    extends = f" (extends {scheme.base_name})" if scheme.base_name != scheme.name else ""
    print(f"\nRoster {roster.crew_id}  ·  scheme: {scheme.name}{extends}")
    print(f"{len(roster.duties)} duties · {span}\n")

    for r in bad:
        print(r)
        print()

    print(f"{len(bad)} violations · {len(results) - len(bad)} rules passed")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
