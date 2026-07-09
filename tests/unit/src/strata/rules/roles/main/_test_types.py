"""Test case types for roles rules."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class SfrRuleTestCase:
    """Roles rule source and expected fault facts."""

    description: str
    rule_code: str
    relative_path: str
    source: str
    expected_codes: tuple[str, ...]
    expected_lines: tuple[int | None, ...]
