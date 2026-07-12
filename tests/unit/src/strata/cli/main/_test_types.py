"""Test case types for isolated CLI entry dispatch."""

from __future__ import annotations

from dataclasses import dataclass

from strata.scaffolding.models import InitOptions


@dataclass(frozen=True)
class EntryDispatchTestCase:
    """CLI argv and expected delegated command runner."""

    description: str
    argv: tuple[str, ...]
    runner_attribute: str
    expected_forwarded_argv: tuple[str, ...]
    expected_exit_code: int


@dataclass(frozen=True)
class EntryUsageTestCase:
    """Unknown CLI input and expected usage response."""

    description: str
    argv: tuple[str, ...]
    expected_usage: str
    expected_exit_code: int


@dataclass(frozen=True)
class InitAdapterTestCase:
    """Init argv and expected core options."""

    description: str
    argv: tuple[str, ...]
    stdout_isatty: bool
    expected_options: InitOptions
    expected_use_color: bool
    expected_exit_code: int


@dataclass(frozen=True)
class InitNoColorTestCase:
    """Environment color override and expected core color choice."""

    description: str
    no_color: str
    expected_use_color: bool
    expected_exit_code: int
