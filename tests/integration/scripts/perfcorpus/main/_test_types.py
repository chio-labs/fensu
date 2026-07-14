"""Test-case types for corpus generation behavior."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class CorpusDeterminismTestCase:
    """One corpus determinism expectation."""

    description: str
    file_target: int
    seed: int
    expected_identical: bool


@dataclass(frozen=True)
class CorpusShapeTestCase:
    """One corpus scale and layout expectation."""

    description: str
    file_target: int
    seed: int
    expected_minimum_domains: int


@dataclass(frozen=True)
class CorpusFaultParityTestCase:
    """One expectation that declared faults match strata output."""

    description: str
    file_target: int
    seed: int
    expected_exit_code: int
