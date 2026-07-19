"""Tests for deterministic parallel evaluation planning."""

from __future__ import annotations

import pytest

from fensu.evaluation._helpers import parallel_evaluation
from fensu.evaluation._helpers.parallel_evaluation import default_worker_count
from tests.unit.src.fensu.evaluation._test_types import (
    DefaultWorkerCountTestCase,
)


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
