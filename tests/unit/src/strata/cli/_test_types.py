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


@dataclass(frozen=True)
class DefaultWorkerCountTestCase:
    """One repository size, host CPU count, and the expected automatic workers."""

    description: str
    target_count: int
    cpu_count: int | None
    expected_workers: int
