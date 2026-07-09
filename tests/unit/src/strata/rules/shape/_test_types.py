"""Test case types for the shape catalogue."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ShapeCatalogueTestCase:
    """Expected shape catalogue facts."""

    description: str
    expected_codes: tuple[str, ...]
    expected_unique_count: int


@dataclass(frozen=True)
class ShapeDefaultOffTestCase:
    """Expected default-off shape rule facts."""

    description: str
    rule_code: str
    expected_enabled_by_default: bool
