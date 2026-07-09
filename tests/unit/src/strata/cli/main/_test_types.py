"""Test case types for CLI behavior."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class CheckCommandTestCase:
    """CLI check command inputs and expected process output."""

    description: str
    argv: tuple[str, ...]
    rule_code: str
    expected_exit_code: int
    expected_output_fragment: str
    expected_no_output_fragment: str


@dataclass(frozen=True)
class CheckNoFaultTestCase:
    """CLI check command inputs and expected no-fault output."""

    description: str
    argv: tuple[str, ...]
    expected_exit_code: int
    expected_output_fragment: str
