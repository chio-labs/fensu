"""Console-script entrypoint for the strata CLI."""

from __future__ import annotations

import sys

from strata.cli.core.types import CliCommand
from strata.cli.main.check import run_check
from strata.cli.main.map import run_map
from strata.cli.main.rule import run_rule
from strata.cli.main.skill import run_skill


def main(argv: tuple[str, ...] | None = None) -> int:
    """Run the strata CLI."""

    args: tuple[str, ...] = tuple(sys.argv[1:] if argv is None else argv)
    if args and args[0] == CliCommand.CHECK:
        return run_check(argv=args[1:])
    if args and args[0] == CliCommand.RULE:
        return run_rule(argv=args[1:])
    if args and args[0] == CliCommand.SKILL:
        return run_skill(argv=args[1:])
    if args and args[0] == CliCommand.MAP:
        return run_map(argv=args[1:])
    sys.stderr.write("Usage: strata {check,rule,skill,map} ...\n")
    return 2
