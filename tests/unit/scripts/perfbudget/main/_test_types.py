"""Test-case types for budget specification resolution."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class SpecResolutionTestCase:
    """One expectation for resolving native budget ceiling overrides."""

    description: str
    uncached_ceiling: float | None
    cold_ceiling: float | None
    warm_ceiling: float | None
    edit_ceiling: float | None
    version_ceiling: float | None
    init_ceiling: float | None
    expected_uncached: float
    expected_cold: float
    expected_warm: float
    expected_edit: float
    expected_version: float
    expected_init: float
