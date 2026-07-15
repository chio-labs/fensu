"""Load only the selected CLI command implementation."""

from __future__ import annotations


def run_check(*, argv: tuple[str, ...] | None = None) -> int:
    """Load and run the check command."""

    from strata.cli.main.check import run_check as command

    return command(argv=argv)


def run_init(*, argv: tuple[str, ...] | None = None) -> int:
    """Load and run the init command."""

    from strata.cli.main.init import run_init as command

    return command(argv=argv)


def run_rule(*, argv: tuple[str, ...] | None = None) -> int:
    """Load and run the rule command."""

    from strata.cli.main.rule import run_rule as command

    return command(argv=argv)


def run_skills(*, argv: tuple[str, ...] | None = None) -> int:
    """Load and run the skills command."""

    from strata.cli.main.skills import run_skills as command

    return command(argv=argv)


def run_map(*, argv: tuple[str, ...] | None = None) -> int:
    """Load and run the map command."""

    from strata.cli.main.map import run_map as command

    return command(argv=argv)
