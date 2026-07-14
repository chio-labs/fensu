"""Test case types for parser validity agreement tests."""

from dataclasses import dataclass


@dataclass(frozen=True)
class RepoParseAgreementTestCase:
    """A tree whose files must classify identically under both parsers."""

    description: str
    expected_divergent: tuple[str, ...]


@dataclass(frozen=True)
class RepoFactParityTestCase:
    """A tree whose fact families must match across backends."""

    description: str
    expected_divergent: tuple[str, ...]
