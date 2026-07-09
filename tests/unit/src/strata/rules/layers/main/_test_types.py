"""Test case types for layer rules."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class LayerRuleTestCase:
    """Layer rule fixture files and expected fault facts."""

    description: str
    rule_code: str
    files: tuple[tuple[str, str], ...]
    expected_codes: tuple[str, ...]
    expected_lines: tuple[int | None, ...]


@dataclass(frozen=True)
class ToolingImportRuleTestCase:
    """Layer rule fixture with tooling scope and expected fault facts."""

    description: str
    files: tuple[tuple[str, str], ...]
    tooling: tuple[str, ...]
    expected_codes: tuple[str, ...]
    expected_lines: tuple[int | None, ...]
