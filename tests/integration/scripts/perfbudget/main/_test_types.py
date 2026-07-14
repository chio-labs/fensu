"""Test-case types for budget scenario behavior."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class BudgetRunTestCase:
    """One complete budget run expectation."""

    description: str
    file_target: int
    seed: int
    ceiling_seconds: float
    expected_exit_code: int
