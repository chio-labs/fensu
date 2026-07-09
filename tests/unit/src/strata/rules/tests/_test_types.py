"""Test case types for the tests rule catalogue."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class SftCatalogueTestCase:
    """Expected tests catalogue facts."""

    description: str
    expected_codes: tuple[str, ...]
    expected_unique_count: int


@dataclass(frozen=True)
class SftGuidanceTestCase:
    """Expected message and remediation for a tests rule."""

    description: str
    rule_code: str
    expected_message: str
    expected_remediation: str
