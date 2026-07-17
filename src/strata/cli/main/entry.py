"""Console-script entrypoint for the strata CLI."""

from __future__ import annotations

import sys
from importlib import metadata

from strata.analysis.exceptions import NativeBackendUnavailableError
from strata.cli._helpers.lazy_commands import (
    run_check,
    run_init,
    run_map,
    run_memory,
    run_rule,
    run_skills,
)
from strata.cli.types import CliCommand, CliOption


def main(argv: tuple[str, ...] | None = None) -> int:
    """Run the strata CLI."""

    args: tuple[str, ...] = tuple(sys.argv[1:] if argv is None else argv)
    if args and args[0] in {CliOption.HELP, CliOption.SHORT_HELP}:
        _write_help()
        return 0
    if args and args[0] == CliOption.VERSION:
        sys.stdout.write(f"strata {_installed_version()}\n")
        return 0
    try:
        if args and args[0] == CliCommand.CHECK:
            return run_check(argv=args[1:])
        if args and args[0] == CliCommand.INIT:
            return run_init(argv=args[1:])
        if args and args[0] == CliCommand.RULE:
            return run_rule(argv=args[1:])
        if args and args[0] == CliCommand.SKILLS:
            return run_skills(argv=args[1:])
        if args and args[0] == CliCommand.MAP:
            return run_map(argv=args[1:])
        if args and args[0] == CliCommand.MEMORY:
            return run_memory(argv=args[1:])
    except NativeBackendUnavailableError as error:
        sys.stderr.write(f"{error}\n")
        return 2
    if args:
        sys.stderr.write(f"Unknown command: {args[0]}\n")
    sys.stderr.write("Usage: strata {check,init,rule,skills,map,memory} ...\n")
    return 2


def _write_help() -> None:
    sys.stdout.write(
        "Usage: strata {init,check,rule,map,skills,memory} ...\n"
        "\n"
        "Commands:\n"
        "  init    Initialize Strata configuration for a repository.\n"
        "  check   Evaluate repository architecture rules.\n"
        "  rule    Show details for one rule.\n"
        "  map     Render a downstream project call map.\n"
        "  skills  Generate and install agent guidance.\n"
        "  memory  Inspect and query persistent repository memory.\n"
        "\n"
        "Run `strata <command> --help` for command-specific options.\n"
    )


def _installed_version() -> str:
    try:
        return metadata.version("stratalint")
    except metadata.PackageNotFoundError:
        return "unknown"
