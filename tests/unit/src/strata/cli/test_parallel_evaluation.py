"""Tests for deterministic parallel evaluation partition planning."""

from __future__ import annotations

from itertools import chain

import pytest

from strata.cli._helpers import parallel_evaluation
from strata.cli._helpers.parallel_evaluation import _contiguous_partitions, default_worker_count
from tests.unit.src.strata.cli._test_types import (
    DefaultWorkerCountTestCase,
    PartitionPlanTestCase,
)


@pytest.mark.parametrize(
    "test_case",
    [
        PartitionPlanTestCase(
            description="even path count splits into equal contiguous partitions",
            paths=("a.py", "b.py", "c.py", "d.py"),
            jobs=2,
            expected_partitions=(("a.py", "b.py"), ("c.py", "d.py")),
        ),
        PartitionPlanTestCase(
            description="remainder paths go to the earliest partitions",
            paths=("a.py", "b.py", "c.py", "d.py", "e.py"),
            jobs=3,
            expected_partitions=(("a.py", "b.py"), ("c.py", "d.py"), ("e.py",)),
        ),
        PartitionPlanTestCase(
            description="more workers than paths collapses to one path per worker",
            paths=("a.py", "b.py"),
            jobs=8,
            expected_partitions=(("a.py",), ("b.py",)),
        ),
        PartitionPlanTestCase(
            description="single worker owns every path in order",
            paths=("a.py", "b.py", "c.py"),
            jobs=1,
            expected_partitions=(("a.py", "b.py", "c.py"),),
        ),
    ],
    ids=lambda case: case.description,
)
def test_given_ordered_paths_when_partitioning_then_returns_contiguous_deterministic_split(
    test_case: PartitionPlanTestCase,
) -> None:
    partitions: tuple[tuple[str, ...], ...] = _contiguous_partitions(
        paths=test_case.paths,
        jobs=test_case.jobs,
    )

    assert partitions == test_case.expected_partitions
    assert tuple(chain.from_iterable(partitions)) == test_case.paths


@pytest.mark.parametrize(
    "test_case",
    [
        DefaultWorkerCountTestCase(
            description="small repositories stay serial below the breakeven size",
            target_count=199,
            cpu_count=16,
            expected_workers=1,
        ),
        DefaultWorkerCountTestCase(
            description="large repositories use the measured worker plateau cap",
            target_count=2400,
            cpu_count=16,
            expected_workers=8,
        ),
        DefaultWorkerCountTestCase(
            description="hosts below the cap use every available cpu",
            target_count=2400,
            cpu_count=4,
            expected_workers=4,
        ),
        DefaultWorkerCountTestCase(
            description="unknown cpu count degrades to serial",
            target_count=2400,
            cpu_count=None,
            expected_workers=1,
        ),
    ],
    ids=lambda case: case.description,
)
def test_given_repository_size_when_resolving_default_workers_then_applies_measured_policy(
    monkeypatch: pytest.MonkeyPatch,
    test_case: DefaultWorkerCountTestCase,
) -> None:
    monkeypatch.setattr(parallel_evaluation.os, "cpu_count", lambda: test_case.cpu_count)

    workers: int = default_worker_count(target_count=test_case.target_count)

    assert workers == test_case.expected_workers
