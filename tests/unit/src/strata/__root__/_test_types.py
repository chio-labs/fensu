"""Test case types for the strata public surface."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class PublicSurfaceTestCase:
    """The exact set of names the strata package should export."""

    description: str
    expected_all: tuple[str, ...]
