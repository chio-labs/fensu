"""Test case types for annotation catalogue tests."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class AnnotationCatalogueTestCase:
    """Expected annotation catalogue facts."""

    description: str
    expected_codes: tuple[str, ...]
    expected_unique_count: int
