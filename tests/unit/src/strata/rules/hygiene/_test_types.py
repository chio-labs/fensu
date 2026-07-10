"""Test case types for the hygiene catalogue."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class HygieneCatalogueTestCase:
    """Expected hygiene catalogue facts."""

    description: str
    expected_codes: tuple[str, ...]
    expected_unique_count: int
    expected_enabled_by_default: tuple[bool, ...]
