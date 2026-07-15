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


@dataclass(frozen=True)
class RssParseTestCase:
    """GNU time output and expected peak RSS value."""

    description: str
    output: str
    expected_max_rss_kib: int | None


@dataclass(frozen=True)
class RepeatedRunValidationTestCase:
    """Repeated output identities and expected validation failures."""

    description: str
    first_hash: str
    second_hash: str
    expected_failure_count: int
