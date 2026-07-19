"""Test case types for the naming catalogue."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class FfnCatalogueTestCase:
    """Expected naming catalogue facts."""

    description: str
    expected_codes: tuple[str, ...]
    expected_unique_count: int


@dataclass(frozen=True)
class FfnSelectionTestCase:
    """Naming selectors and expected active naming codes."""

    description: str
    select: tuple[str, ...]
    ignore: tuple[str, ...]
    expected_codes: tuple[str, ...]
