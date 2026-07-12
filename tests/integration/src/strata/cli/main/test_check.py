"""Tests for `strata check` orchestration."""

from __future__ import annotations

from pathlib import Path

import pytest

from strata.cache.fingerprints.models import GlobalFingerprintBuild
from strata.cache.results.classes.result_cache import ResultCache
from strata.cache.results.models import CacheStats
from strata.cache.storage.exceptions import CacheRecordError
from strata.cli.main.check import run_check
from tests.integration.src.strata.cli.main._test_types import (
    CheckCacheModeTestCase,
    CheckCacheWarningTestCase,
    CheckCommandTestCase,
    CheckErrorTestCase,
    CheckNoFaultTestCase,
)
from tests.integration.src.strata.cli.main.helpers import (
    CaptureOutput,
    cache_snapshot,
    write_cli_core_fault_project,
    write_cli_exception_project,
    write_cli_fixture_project,
    write_cli_no_fault_project,
    write_cli_stale_exception_project,
)


@pytest.mark.parametrize(
    "test_case",
    [
        CheckCommandTestCase(
            description="custom rule fault returns exit one and text output",
            argv=("--no-color",),
            rule_code="XCK001",
            expected_exit_code=1,
            expected_output_fragment=(
                "XCK001  custom fault\n"
                " --> src/pkg/target.py:1:0\n"
                "  |\n"
                "1 | value: int = 1\n"
                "  | ^\n"
                "  |\n"
                "  = help: apply the custom remediation\n"
                "\n"
                "Found 1 fault"
            ),
            expected_no_output_fragment="\033[",
        )
    ],
    ids=lambda case: case.description,
)
def test_given_custom_rule_fault_when_running_check_then_outputs_report_and_exit_one(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    test_case: CheckCommandTestCase,
) -> None:
    write_cli_fixture_project(root=tmp_path, rule_code=test_case.rule_code)
    monkeypatch.chdir(tmp_path)
    stdout: CaptureOutput = CaptureOutput(is_terminal=True)
    stderr: CaptureOutput = CaptureOutput()

    exit_code: int = run_check(argv=test_case.argv, stdout=stdout, stderr=stderr)

    assert exit_code == test_case.expected_exit_code
    assert test_case.expected_output_fragment in stdout.getvalue()
    assert test_case.expected_no_output_fragment not in stdout.getvalue()


@pytest.mark.parametrize(
    "test_case",
    [
        CheckCommandTestCase(
            description="nested invocation uses config-relative roots and custom rules",
            argv=("--no-color",),
            rule_code="XCK002",
            expected_exit_code=1,
            expected_output_fragment="XCK002  custom fault",
            expected_no_output_fragment="Configured root path",
        )
    ],
    ids=lambda case: case.description,
)
def test_given_nested_working_directory_when_running_check_then_uses_config_directory(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    test_case: CheckCommandTestCase,
) -> None:
    write_cli_fixture_project(root=tmp_path, rule_code=test_case.rule_code)
    nested: Path = tmp_path / "src/pkg/nested"
    nested.mkdir()
    monkeypatch.chdir(nested)
    stdout: CaptureOutput = CaptureOutput()
    stderr: CaptureOutput = CaptureOutput()

    exit_code: int = run_check(argv=test_case.argv, stdout=stdout, stderr=stderr)

    assert exit_code == test_case.expected_exit_code
    assert test_case.expected_output_fragment in stdout.getvalue()
    assert test_case.expected_no_output_fragment not in stderr.getvalue()


@pytest.mark.parametrize(
    "test_case",
    [
        CheckNoFaultTestCase(
            description="no faults returns exit zero with summary",
            argv=("--no-color",),
            expected_exit_code=0,
            expected_output_fragment="Found 0 faults",
        )
    ],
    ids=lambda case: case.description,
)
def test_given_no_faults_when_running_check_then_outputs_summary_and_exit_zero(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    test_case: CheckNoFaultTestCase,
) -> None:
    write_cli_no_fault_project(tmp_path)
    monkeypatch.chdir(tmp_path)
    stdout: CaptureOutput = CaptureOutput(is_terminal=True)
    stderr: CaptureOutput = CaptureOutput()

    exit_code: int = run_check(argv=test_case.argv, stdout=stdout, stderr=stderr)

    assert exit_code == test_case.expected_exit_code
    assert test_case.expected_output_fragment in stdout.getvalue()


@pytest.mark.parametrize(
    "test_case",
    [
        CheckNoFaultTestCase(
            description="applied exception reports count when check otherwise passes",
            argv=("--no-color",),
            expected_exit_code=0,
            expected_output_fragment="Found 0 faults\nApplied 1 rule exception",
        )
    ],
    ids=lambda case: case.description,
)
def test_given_applied_exception_when_running_check_then_reports_count_and_exit_zero(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    test_case: CheckNoFaultTestCase,
) -> None:
    write_cli_exception_project(tmp_path)
    monkeypatch.chdir(tmp_path)
    stdout: CaptureOutput = CaptureOutput()

    exit_code: int = run_check(argv=test_case.argv, stdout=stdout)

    assert exit_code == test_case.expected_exit_code
    assert test_case.expected_output_fragment in stdout.getvalue()


@pytest.mark.parametrize(
    "test_case",
    [
        CheckErrorTestCase(
            description="stale exception returns configuration error and removal guidance",
            argv=("--no-color",),
            expected_exit_code=2,
            expected_error_fragment="Stale rule exception(s) suppressed no faults; remove them",
        )
    ],
    ids=lambda case: case.description,
)
def test_given_stale_exception_when_running_check_then_reports_actionable_error(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    test_case: CheckErrorTestCase,
) -> None:
    write_cli_stale_exception_project(tmp_path)
    monkeypatch.chdir(tmp_path)
    stderr: CaptureOutput = CaptureOutput()

    exit_code: int = run_check(argv=test_case.argv, stderr=stderr)

    assert exit_code == test_case.expected_exit_code
    assert test_case.expected_error_fragment in stderr.getvalue()


@pytest.mark.parametrize(
    "test_case",
    [
        CheckCacheModeTestCase(
            description="cold warm and no-cache modes preserve output without warm writes",
            cached_argv=("--no-color", "--cache"),
            uncached_argv=("--no-color", "--no-cache"),
            expected_exit_code=1,
            expected_output_fragment="SFA101",
            expected_cache_exists=True,
        )
    ],
    ids=lambda case: case.description,
)
def test_given_cacheable_project_when_running_modes_then_preserves_output_and_warm_storage(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    test_case: CheckCacheModeTestCase,
) -> None:
    write_cli_core_fault_project(tmp_path)
    monkeypatch.chdir(tmp_path)
    cold_stdout: CaptureOutput = CaptureOutput()
    warm_stdout: CaptureOutput = CaptureOutput()
    uncached_stdout: CaptureOutput = CaptureOutput()

    cold_exit: int = run_check(argv=test_case.cached_argv, stdout=cold_stdout)
    cold_snapshot: tuple[tuple[str, bytes], ...] = cache_snapshot(tmp_path)
    warm_exit: int = run_check(argv=test_case.cached_argv, stdout=warm_stdout)
    warm_snapshot: tuple[tuple[str, bytes], ...] = cache_snapshot(tmp_path)
    uncached_exit: int = run_check(argv=test_case.uncached_argv, stdout=uncached_stdout)
    uncached_snapshot: tuple[tuple[str, bytes], ...] = cache_snapshot(tmp_path)

    assert cold_exit == test_case.expected_exit_code
    assert warm_exit == test_case.expected_exit_code
    assert uncached_exit == test_case.expected_exit_code
    assert test_case.expected_output_fragment in cold_stdout.getvalue()
    assert warm_stdout.getvalue() == cold_stdout.getvalue()
    assert uncached_stdout.getvalue() == cold_stdout.getvalue()
    assert bool(cold_snapshot) is test_case.expected_cache_exists
    assert warm_snapshot == cold_snapshot
    assert uncached_snapshot == cold_snapshot


@pytest.mark.parametrize(
    "test_case",
    [
        CheckCacheModeTestCase(
            description="no-cache skips fingerprinting and creates no storage",
            cached_argv=("--no-color", "--cache"),
            uncached_argv=("--no-color", "--no-cache"),
            expected_exit_code=1,
            expected_output_fragment="SFA101",
            expected_cache_exists=False,
        )
    ],
    ids=lambda case: case.description,
)
def test_given_fresh_project_when_running_no_cache_then_bypasses_all_cache_work(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    test_case: CheckCacheModeTestCase,
) -> None:
    write_cli_core_fault_project(tmp_path)
    monkeypatch.chdir(tmp_path)
    stdout: CaptureOutput = CaptureOutput()

    def fail_fingerprint(**kwargs: object) -> None:
        del kwargs
        raise AssertionError("no-cache attempted global fingerprinting")

    monkeypatch.setattr("strata.cli.main.check.build_global_fingerprint", fail_fingerprint)

    exit_code: int = run_check(argv=test_case.uncached_argv, stdout=stdout)

    assert exit_code == test_case.expected_exit_code
    assert test_case.expected_output_fragment in stdout.getvalue()
    assert (tmp_path / ".strata").exists() is test_case.expected_cache_exists


@pytest.mark.parametrize(
    "test_case",
    [
        CheckCacheWarningTestCase(
            description="internal cache error warns on stderr and preserves diagnostics",
            argv=("--no-color", "--cache"),
            expected_exit_code=1,
            expected_output_fragment="SFA101",
            expected_warning_fragment="internal cache error",
        )
    ],
    ids=lambda case: case.description,
)
def test_given_internal_cache_error_when_running_check_then_warns_and_preserves_output(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    test_case: CheckCacheWarningTestCase,
) -> None:
    write_cli_core_fault_project(tmp_path)
    monkeypatch.chdir(tmp_path)
    stdout: CaptureOutput = CaptureOutput()
    stderr: CaptureOutput = CaptureOutput()

    def raise_publish(cache: ResultCache, **kwargs: object) -> CacheStats:
        del cache, kwargs
        raise CacheRecordError("publication rejected")

    monkeypatch.setattr(ResultCache, "publish", raise_publish)

    exit_code: int = run_check(argv=test_case.argv, stdout=stdout, stderr=stderr)

    assert exit_code == test_case.expected_exit_code
    assert test_case.expected_output_fragment in stdout.getvalue()
    assert test_case.expected_warning_fragment in stderr.getvalue()


@pytest.mark.parametrize(
    "test_case",
    [
        CheckCacheModeTestCase(
            description="incomplete global identity falls back to uncached evaluation",
            cached_argv=("--no-color", "--cache"),
            uncached_argv=("--no-color", "--no-cache"),
            expected_exit_code=1,
            expected_output_fragment="SFA101",
            expected_cache_exists=False,
        )
    ],
    ids=lambda case: case.description,
)
def test_given_incomplete_global_identity_when_running_cache_then_falls_back_safely(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    test_case: CheckCacheModeTestCase,
) -> None:
    write_cli_core_fault_project(tmp_path)
    monkeypatch.chdir(tmp_path)
    stdout: CaptureOutput = CaptureOutput()

    monkeypatch.setattr(
        "strata.cli.main.check.build_global_fingerprint",
        lambda **kwargs: GlobalFingerprintBuild(
            fingerprint=None,
            disabled_reason="the loaded implementation files are unavailable",
        ),
    )

    exit_code: int = run_check(argv=test_case.cached_argv, stdout=stdout)

    assert exit_code == test_case.expected_exit_code
    assert test_case.expected_output_fragment in stdout.getvalue()
    assert (tmp_path / ".strata").exists() is test_case.expected_cache_exists


@pytest.mark.parametrize(
    "test_case",
    [
        CheckCacheWarningTestCase(
            description="disabled cache reports its reason under cache stats",
            argv=("--no-color", "--cache", "--cache-stats"),
            expected_exit_code=1,
            expected_output_fragment="SFA101",
            expected_warning_fragment=(
                "Cache: disabled (the loaded implementation files are unavailable)"
            ),
        )
    ],
    ids=lambda case: case.description,
)
def test_given_disabled_cache_when_requesting_stats_then_reports_disabled_reason(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    test_case: CheckCacheWarningTestCase,
) -> None:
    write_cli_core_fault_project(tmp_path)
    monkeypatch.chdir(tmp_path)
    stdout: CaptureOutput = CaptureOutput()
    stderr: CaptureOutput = CaptureOutput()

    monkeypatch.setattr(
        "strata.cli.main.check.build_global_fingerprint",
        lambda **kwargs: GlobalFingerprintBuild(
            fingerprint=None,
            disabled_reason="the loaded implementation files are unavailable",
        ),
    )

    exit_code: int = run_check(argv=test_case.argv, stdout=stdout, stderr=stderr)

    assert exit_code == test_case.expected_exit_code
    assert test_case.expected_output_fragment in stdout.getvalue()
    assert test_case.expected_warning_fragment in stderr.getvalue()
