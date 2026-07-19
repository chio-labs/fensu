"""Tests for reproducible benchmark command execution."""

from __future__ import annotations

import subprocess
from io import StringIO
from pathlib import Path

import pytest

from fensu.cli.main.check import run_check
from scripts.benchmarking._helpers.profiling import profile_operations
from scripts.benchmarking.classes.check_profiler import CheckProfiler
from scripts.benchmarking.models import OperationReport, ProfileReport
from scripts.benchmarking.types import OperationProfileMode
from tests.integration.scripts.benchmarking.main._test_types import (
    BenchmarkErrorTestCase,
    OperationProfileTestCase,
    ProcessBenchmarkTestCase,
    ProfileBenchmarkTestCase,
    ProfileCommandTestCase,
)
from tests.integration.scripts.benchmarking.main.helpers import (
    run_benchmark_command,
    run_profile_benchmark_command,
    write_custom_rule_profile_project,
    write_fake_fensu,
    write_profile_project,
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
    executable: Path = write_fake_fensu(root=tmp_path, output=test_case.output)

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
    executable: Path = write_fake_fensu(root=tmp_path, output="", changing=True)

    completed: subprocess.CompletedProcess[str] = run_benchmark_command(
        project=tmp_path,
        executable=executable,
        runs=test_case.runs,
    )

    assert completed.returncode == 2
    assert test_case.expected_error_fragment in completed.stderr


@pytest.mark.parametrize(
    "test_case",
    [
        ProfileBenchmarkTestCase(
            description="profiler forwards the complete rule execution contract",
            expected_file_count=1,
            expected_rule_count=1,
        )
    ],
    ids=lambda case: case.description,
)
def test_given_profile_project_when_running_profiler_then_completes_instrumented_check(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    test_case: ProfileBenchmarkTestCase,
) -> None:
    write_profile_project(tmp_path)
    monkeypatch.chdir(tmp_path)
    stdout: StringIO = StringIO()
    exit_code: int = run_check(argv=("--no-color", "--no-cache"), stdout=stdout)

    report: ProfileReport = CheckProfiler().run(tmp_path)

    assert exit_code == 0
    assert report.file_count == test_case.expected_file_count
    assert report.rule_count == test_case.expected_rule_count
    assert report.rendered_bytes == len(stdout.getvalue().removesuffix("\n").encode("utf-8"))


@pytest.mark.parametrize(
    "test_case",
    [
        ProfileCommandTestCase(
            description="external scripts package custom rule loads in profiler subprocess",
            expected_rule_code="XBP001",
            expected_output_fragments=("files=1 faults=0 rules=1", "XBP001", "calls=1"),
        )
    ],
    ids=lambda case: case.description,
)
def test_given_external_custom_rule_project_when_profiling_then_command_loads_target_package(
    tmp_path: Path,
    test_case: ProfileCommandTestCase,
) -> None:
    write_custom_rule_profile_project(root=tmp_path, rule_code=test_case.expected_rule_code)

    completed: subprocess.CompletedProcess[str] = run_profile_benchmark_command(project=tmp_path)

    assert completed.returncode == 0
    assert all(fragment in completed.stdout for fragment in test_case.expected_output_fragments)


@pytest.mark.parametrize(
    "test_case",
    [
        OperationProfileTestCase(
            description="warm operation profile includes shared phases and cache bytes",
            mode="warm",
            expected_operations=(
                "cache_record_bytes_read",
                "phase_cache_evaluation_nanoseconds",
                "phase_discovery_nanoseconds",
                "phase_global_fingerprint_nanoseconds",
            ),
        )
    ],
    ids=lambda case: case.description,
)
def test_given_warm_project_when_profiling_operations_then_reports_shared_boundaries(
    tmp_path: Path,
    test_case: OperationProfileTestCase,
) -> None:
    write_profile_project(tmp_path)

    report: OperationReport = profile_operations(
        project=tmp_path,
        mode=OperationProfileMode(test_case.mode),
    )

    operation_names: tuple[str, ...] = tuple(name for name, _ in report.counts)
    assert all(name in operation_names for name in test_case.expected_operations)
