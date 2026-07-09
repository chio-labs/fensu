"""Test case types for annotation rules."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class AnnotationRuleTestCase:
    """Annotation rule source and expected fault facts."""

    description: str
    rule_code: str
    source: str
    expected_codes: tuple[str, ...]
    expected_lines: tuple[int | None, ...]
