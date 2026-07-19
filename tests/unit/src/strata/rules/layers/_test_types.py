"""Test case types for layer rule catalogue tests."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class LayerCatalogueTestCase:
    """Expected layer catalogue facts."""

    description: str
    expected_codes: tuple[str, ...]
    expected_unique_count: int
