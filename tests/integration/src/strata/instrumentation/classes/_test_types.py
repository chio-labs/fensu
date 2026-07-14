"""Test-case types for engine operation-count invariants."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class UncachedCountsTestCase:
    """One uncached-run operation envelope expectation."""

    description: str
    file_target: int
    seed: int
    expected_relative_path_computes: int


@dataclass(frozen=True)
class CachedCountsTestCase:
    """One cold-then-warm operation envelope expectation."""

    description: str
    file_target: int
    seed: int
    expected_warm_fresh_evaluations: int
    expected_warm_parses: int


@dataclass(frozen=True)
class EditCountsTestCase:
    """One single-file-edit incremental expectation."""

    description: str
    file_target: int
    seed: int
    expected_fresh_evaluations: int
    expected_parses: int
