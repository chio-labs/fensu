"""Test-case types for budget scenario behavior."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class BudgetRunTestCase:
    """One complete budget run expectation."""

    description: str
    backend: str
    file_target: int
    seed: int
    ceiling_seconds: float
    expected_exit_code: int


@dataclass(frozen=True)
class NativeUnavailableTestCase:
    """One expectation for requesting the native backend without the extension."""

    description: str
    expected_exit_code: int
