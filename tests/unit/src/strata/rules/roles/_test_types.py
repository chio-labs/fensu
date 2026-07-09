"""Test case types for the roles catalogue."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class SfrCatalogueTestCase:
    """Expected roles catalogue facts."""

    description: str
    expected_codes: tuple[str, ...]
    expected_unique_count: int
