"""Structured inputs and outputs for budget scenario runs."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class BudgetSpec:
    """One complete budget run request."""

    executable: Path
    file_target: int
    seed: int
    uncached_ceiling: float
    cold_ceiling: float
    warm_ceiling: float
    edit_ceiling: float


@dataclass(frozen=True, slots=True)
class ScenarioResult:
    """One measured check scenario."""

    name: str
    seconds: float
    exit_code: int
    output_sha256: str
    cache_stats: str


@dataclass(frozen=True, slots=True)
class ScenarioFailure:
    """One violated budget or invariant."""

    scenario: str
    reason: str
