"""Test-case types for performance scenario source changes."""

from dataclasses import dataclass


@dataclass(frozen=True)
class SourceRatioChangeTestCase:
    """One source population, ratio, and expected changed count."""

    description: str
    file_count: int
    numerator: int
    denominator: int
    expected_changed_count: int
