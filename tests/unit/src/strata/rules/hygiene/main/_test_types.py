"""Test case types for hygiene rules."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class HygieneRuleTestCase:
    """Hygiene rule source and expected fault facts."""

    description: str
    rule_code: str
    source: str
    expected_codes: tuple[str, ...]
    expected_lines: tuple[int | None, ...]
