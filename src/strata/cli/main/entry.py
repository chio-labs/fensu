"""Console-script entrypoint for the strata CLI."""

from __future__ import annotations

import sys

from strata.cli.main.check import run_check


def main(argv: tuple[str, ...] | None = None) -> int:
    """Run the strata CLI."""

    args: tuple[str, ...] = tuple(sys.argv[1:] if argv is None else argv)
    if args and args[0] == "check":
        return run_check(argv=args[1:])
    sys.stderr.write("Usage: strata check [--no-color] [paths...]\n")
    return 2
