"""Test case types for naming rules."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class SfnRuleTestCase:
    """Naming rule source and expected fault facts."""

    description: str
    source: str
    expected_codes: tuple[str, ...]
    expected_lines: tuple[int | None, ...]
    contracts: dict[str, str] = field(default_factory=dict)
