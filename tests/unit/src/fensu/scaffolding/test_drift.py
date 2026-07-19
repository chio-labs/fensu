"""Tests for real-project drift aggregation."""

from __future__ import annotations

from pathlib import Path

import pytest

from fensu.cache.storage.constants import CACHE_DATABASE_RELATIVE_PATH
from fensu.config.models import Config
from fensu.scaffolding._helpers.drift import measure_drift
from fensu.scaffolding.models import DriftSummary
from tests.unit.src.fensu.scaffolding._test_types import DriftTestCase
from tests.unit.src.fensu.scaffolding.helpers import build_repository


@pytest.mark.parametrize(
    "test_case",
    [
        DriftTestCase(
            description="gradual rules aggregate selected annotation and hygiene families",
            source_text="def run(value):\n    assert value\n",
            select=("FFA", "FFH"),
            expected_family_codes=("FFA", "FFH"),
            expected_family_counts=(2, 1),
            expected_fault_count=3,
            expected_file_count=1,
        ),
        DriftTestCase(
            description="clean selected naming family remains present with zero count",
            source_text="value: int = 1\n",
            select=("FFN",),
            expected_family_codes=("FFN",),
            expected_family_counts=(0,),
            expected_fault_count=0,
            expected_file_count=0,
        ),
    ],
    ids=lambda case: case.description,
)
def test_given_tiny_real_project_when_measuring_drift_then_aggregates_selected_families(
    test_case: DriftTestCase, tmp_path: Path
) -> None:
    build_repository(root=tmp_path, files=(("src/pkg/example.py", test_case.source_text),))
    config: Config = Config(roots=("src/pkg",), tests=(), select=test_case.select)

    summary: DriftSummary = measure_drift(repository=tmp_path, config=config)
    replayed: DriftSummary = measure_drift(repository=tmp_path, config=config)

    assert tuple(code for code, _, _ in summary.family_counts) == test_case.expected_family_codes
    assert tuple(count for _, _, count in summary.family_counts) == test_case.expected_family_counts
    assert summary.fault_count == test_case.expected_fault_count
    assert summary.file_count == test_case.expected_file_count
    assert replayed == summary
    assert (tmp_path / CACHE_DATABASE_RELATIVE_PATH).is_file()
