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
    relative_path: str = "src/pkg/domain/core/models.py"
    roots: tuple[str, ...] = ("src/pkg",)
    tooling: tuple[str, ...] = ()
