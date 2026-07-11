"""Test case types for isolated CLI entry dispatch."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class EntryDispatchTestCase:
    """CLI argv and expected delegated command runner."""

    description: str
    argv: tuple[str, ...]
    runner_attribute: str
    expected_forwarded_argv: tuple[str, ...]
    expected_exit_code: int
