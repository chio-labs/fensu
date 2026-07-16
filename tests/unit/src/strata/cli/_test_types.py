"""Test case types for CLI parallel evaluation planning."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class PartitionPlanTestCase:
    """Ordered paths, a worker request count, and the expected contiguous split."""

    description: str
    paths: tuple[str, ...]
    jobs: int
    expected_partitions: tuple[tuple[str, ...], ...]
