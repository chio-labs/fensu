"""Tests for reproducible benchmark command execution."""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from tests.unit.scripts.benchmarking.main._test_types import (
    BenchmarkErrorTestCase,
    ProcessBenchmarkTestCase,
)
from tests.unit.scripts.benchmarking.main.helpers import (
    run_benchmark_command,
    write_fake_strata,
)


@pytest.mark.parametrize(
    "test_case",
    [
        ProcessBenchmarkTestCase(
            description="stable diagnostics produce repeatable identity and timings",
            runs=2,
            output="Found 3 faults\n",
            expected_sha256="00a7fd9ff81d43aaf5daf6521f602cdc09b90387f100cf189e889a4239c61c85",
            expected_summary="Found 3 faults",
            expected_output_bytes=15,
        )
    ],
    ids=lambda case: case.description,
)
def test_given_stable_check_when_running_benchmark_then_reports_diagnostic_identity(
    tmp_path: Path,
    test_case: ProcessBenchmarkTestCase,
) -> None:
    executable: Path = write_fake_strata(root=tmp_path, output=test_case.output)

    completed: subprocess.CompletedProcess[str] = run_benchmark_command(
        project=tmp_path,
        executable=executable,
        runs=test_case.runs,
    )

    assert completed.returncode == 0
    assert f"output_sha256={test_case.expected_sha256}" in completed.stdout
    assert f"summary={test_case.expected_summary}" in completed.stdout
    assert f"output_bytes={test_case.expected_output_bytes}" in completed.stdout
    assert "median_seconds=" in completed.stdout


@pytest.mark.parametrize(
    "test_case",
    [
        BenchmarkErrorTestCase(
            description="changing diagnostics abort benchmark comparison",
            runs=2,
            expected_error_fragment="diagnostics changed",
        )
    ],
    ids=lambda case: case.description,
)
def test_given_changing_check_when_running_benchmark_then_returns_clear_error(
    tmp_path: Path,
    test_case: BenchmarkErrorTestCase,
) -> None:
    executable: Path = write_fake_strata(root=tmp_path, output="", changing=True)

    completed: subprocess.CompletedProcess[str] = run_benchmark_command(
        project=tmp_path,
        executable=executable,
        runs=test_case.runs,
    )

    assert completed.returncode == 2
    assert test_case.expected_error_fragment in completed.stderr
