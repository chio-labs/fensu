"""Test case types for the strata public surface."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class PublicSurfaceTestCase:
    """The exact set of names the strata package should export."""

    description: str
    expected_all: tuple[str, ...]
    expected_threshold_value: str


@dataclass(frozen=True)
class LazyPublicSurfaceTestCase:
    """One public module that a bare package import must not load."""

    description: str
    expected_absent_module: str
    expected_return_code: int
