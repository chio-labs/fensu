"""Tests for `strata check` orchestration."""

from __future__ import annotations

from pathlib import Path

import pytest

from strata.cache.fingerprints.models import GlobalFingerprintBuild
from strata.cache.results.classes.result_cache import ResultCache
from strata.cache.results.models import CacheStats
from strata.cache.storage.constants import CACHE_DATABASE_RELATIVE_PATH
from strata.cache.storage.exceptions import CacheRecordError
from strata.cli.main.check import run_check
from tests.integration.src.strata.cli.main._test_types import (
    CheckCacheModeTestCase,
    CheckCachePreferenceTestCase,
    CheckCacheWarningTestCase,
    CheckCommandTestCase,
    CheckErrorTestCase,
    CheckNoFaultTestCase,
    EvaluationCheckTestCase,
    NestedContainerCacheTestCase,
    ThresholdOverrideCheckTestCase,
)
from tests.integration.src.strata.cli.main.helpers import (
    CaptureOutput,
    cache_snapshot,
    write_cli_core_fault_project,
    write_cli_exception_project,
    write_cli_file_exception_project,
    write_cli_fixture_project,
    write_cli_no_fault_project,
    write_cli_stale_exception_project,
)


@pytest.mark.parametrize(
    "test_case",
    [
        EvaluationCheckTestCase(
            description="configured filter has byte-identical cached and uncached reporting",
            expected_exit_code=1,
            expected_summary="Evaluation: 1 of 2 Python files (1 excluded by config)\n",
            expected_fault_fragment="src/pkg/target.py",
            expected_absent_fragment="src/pkg/context.py",
        )
    ],
    ids=lambda case: case.description,
)
def test_given_evaluation_filter_when_running_check_then_reports_exact_cached_parity(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    test_case: EvaluationCheckTestCase,
) -> None:
    (tmp_path / "strata.toml").write_text(
        'roots = ["src/pkg"]\ntests = []\nselect = ["SFA101"]\n'
        "[evaluation]\n"
        'include = ["src/pkg/target.py"]\n'
        'exclude = ["**/generated/**"]\n',
        encoding="utf-8",
    )
    package: Path = tmp_path / "src/pkg"
    package.mkdir(parents=True)
    (package / "target.py").write_text("TARGET = 1\n", encoding="utf-8")
    (package / "context.py").write_text("CONTEXT = 1\n", encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    cached_stdout: CaptureOutput = CaptureOutput()
    uncached_stdout: CaptureOutput = CaptureOutput()

    cached_exit: int = run_check(
        argv=("--no-color", "--cache"), stdout=cached_stdout, stderr=CaptureOutput()
    )
    uncached_exit: int = run_check(
        argv=("--no-color", "--no-cache"), stdout=uncached_stdout, stderr=CaptureOutput()
    )

    assert cached_exit == test_case.expected_exit_code
    assert uncached_exit == test_case.expected_exit_code
    assert cached_stdout.getvalue() == uncached_stdout.getvalue()
    assert cached_stdout.getvalue().startswith(test_case.expected_summary)
    assert test_case.expected_fault_fragment in cached_stdout.getvalue()
    assert test_case.expected_absent_fragment not in cached_stdout.getvalue()


@pytest.mark.parametrize(
    "test_case",
    [
        CheckErrorTestCase(
            description="zero evaluation targets exit two with actionable error",
            argv=("--no-color", "--no-cache"),
            expected_exit_code=2,
            expected_error_fragment="selects zero Python files",
        )
    ],
    ids=lambda case: case.description,
)
def test_given_zero_evaluation_targets_when_running_check_then_exits_two(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    test_case: CheckErrorTestCase,
) -> None:
    (tmp_path / "strata.toml").write_text(
        'roots = ["src/pkg"]\ntests = []\n[evaluation]\nexclude = ["**"]\n',
        encoding="utf-8",
    )
    package: Path = tmp_path / "src/pkg"
    package.mkdir(parents=True)
    (package / "target.py").write_text("TARGET: int = 1\n", encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    stdout: CaptureOutput = CaptureOutput()
    stderr: CaptureOutput = CaptureOutput()

    exit_code: int = run_check(argv=test_case.argv, stdout=stdout, stderr=stderr)

    assert exit_code == test_case.expected_exit_code
    assert test_case.expected_error_fragment in stderr.getvalue()
    assert stdout.getvalue() == ""


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
        CheckNoFaultTestCase(
            description="legal raised container override is reported with effective count",
            argv=("--no-color", "--no-cache"),
            expected_exit_code=0,
            expected_output_fragment=(
                "Applied 1 threshold override\n"
                "Threshold override: max_helpers_container_modules=2 "
                "path=src/pkg/orders/_helpers/parsing/__init__.py "
                "pattern=src/pkg/**/_helpers/parsing/__init__.py order=0 "
                'reason="Parser breadth."'
            ),
        )
    ],
    ids=lambda case: case.description,
)
def test_given_legal_threshold_override_when_running_check_then_reports_usage(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    test_case: CheckNoFaultTestCase,
) -> None:
    config_path: Path = tmp_path / "strata.toml"
    config_path.write_text(
        'roots = ["src/pkg"]\nselect = ["SFR301"]\n'
        "[thresholds]\nmax_helpers_container_modules = 1\n"
        "[[threshold_overrides]]\n"
        'paths = ["src/pkg/**/_helpers/parsing/__init__.py"]\n'
        'reason = "Parser breadth."\n'
        "thresholds = { max_helpers_container_modules = 2 }\n",
        encoding="utf-8",
    )
    bucket: Path = tmp_path / "src/pkg/orders/_helpers/parsing"
    bucket.mkdir(parents=True)
    for name in ("__init__.py", "first.py", "second.py"):
        (bucket / name).write_text("", encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    stdout: CaptureOutput = CaptureOutput(is_terminal=True)

    exit_code: int = run_check(argv=test_case.argv, stdout=stdout)

    assert exit_code == test_case.expected_exit_code
    assert test_case.expected_output_fragment in stdout.getvalue()


@pytest.mark.parametrize(
    "test_case",
    [
        ThresholdOverrideCheckTestCase(
            description="active threshold rule preserves override use across cold and warm cache",
            selected_rule="SFR301",
            override_value=2,
            expected_output_fragment="Applied 1 threshold override",
            expected_additional_fragment="max_helpers_container_modules=2",
            expected_reason_fragment='reason="Parser \\"breadth\\".\\nControlled."',
            expected_absent_fragment="Applied 2 threshold overrides",
            expected_exit_code=0,
        ),
        ThresholdOverrideCheckTestCase(
            description="inactive threshold rule records no override use",
            selected_rule="SFA101",
            override_value=2,
            expected_output_fragment="Found 0 faults",
            expected_additional_fragment="Found 0 faults",
            expected_reason_fragment="Found 0 faults",
            expected_absent_fragment="Threshold override:",
            expected_exit_code=0,
        ),
        ThresholdOverrideCheckTestCase(
            description="faulting threshold override reports actual use across cache",
            selected_rule="SFR301",
            override_value=1,
            expected_output_fragment="Applied 1 threshold override",
            expected_additional_fragment="SFR301  _helpers/ container has 2 modules",
            expected_reason_fragment='reason="Parser \\"breadth\\".\\nControlled."',
            expected_absent_fragment="Applied 2 threshold overrides",
            expected_exit_code=1,
        ),
    ],
    ids=lambda case: case.description,
)
def test_given_threshold_override_when_running_cached_check_then_reports_only_actual_uses(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    test_case: ThresholdOverrideCheckTestCase,
) -> None:
    config_path: Path = tmp_path / "strata.toml"
    config_path.write_text(
        f'roots = ["src/pkg"]\nselect = ["{test_case.selected_rule}"]\n'
        "[[threshold_overrides]]\n"
        'paths = ["src/pkg/**/_helpers/parsing/__init__.py"]\n'
        'reason = "Parser \\"breadth\\".\\nControlled."\n'
        f"thresholds = {{ max_helpers_container_modules = {test_case.override_value} }}\n",
        encoding="utf-8",
    )
    bucket: Path = tmp_path / "src/pkg/orders/_helpers/parsing"
    bucket.mkdir(parents=True)
    for name in ("__init__.py", "first.py", "second.py"):
        (bucket / name).write_text("", encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    cold_stdout: CaptureOutput = CaptureOutput()
    warm_stdout: CaptureOutput = CaptureOutput()

    cold_exit: int = run_check(argv=("--no-color", "--cache"), stdout=cold_stdout)
    warm_exit: int = run_check(argv=("--no-color", "--cache"), stdout=warm_stdout)

    assert cold_exit == test_case.expected_exit_code
    assert warm_exit == test_case.expected_exit_code
    assert warm_stdout.getvalue() == cold_stdout.getvalue()
    assert test_case.expected_output_fragment in cold_stdout.getvalue()
    assert test_case.expected_additional_fragment in cold_stdout.getvalue()
    assert test_case.expected_reason_fragment in cold_stdout.getvalue()
    assert test_case.expected_absent_fragment not in cold_stdout.getvalue()


@pytest.mark.parametrize(
    "test_case",
    [
        NestedContainerCacheTestCase(
            description="nested bucket fault remains fully cacheable with identical output",
            expected_exit_code=1,
            expected_fault_fragment="SFR301  _helpers/ container has 2 modules",
            expected_summary_fragment="Found 1 fault",
            expected_cold_stats_fragment="hits=0 misses=4",
            expected_warm_stats_fragment="hits=4 misses=0",
            expected_non_cacheable_fragment="non_cacheable=0",
        )
    ],
    ids=lambda case: case.description,
)
def test_given_nested_container_fault_when_running_cold_and_warm_then_reuses_all_results(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    test_case: NestedContainerCacheTestCase,
) -> None:
    (tmp_path / "strata.toml").write_text(
        'roots = ["src/pkg"]\nselect = ["SFR301"]\n'
        "[thresholds]\nmax_helpers_container_modules = 1\n",
        encoding="utf-8",
    )
    helpers: Path = tmp_path / "src/pkg/orders/_helpers"
    bucket: Path = helpers / "parsing"
    bucket.mkdir(parents=True)
    for path in (
        helpers / "__init__.py",
        bucket / "__init__.py",
        bucket / "first.py",
        bucket / "second.py",
    ):
        path.write_text("", encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    cold_stdout: CaptureOutput = CaptureOutput()
    cold_stderr: CaptureOutput = CaptureOutput()
    warm_stdout: CaptureOutput = CaptureOutput()
    warm_stderr: CaptureOutput = CaptureOutput()
    argv: tuple[str, ...] = ("--no-color", "--cache", "--cache-stats")

    cold_exit: int = run_check(argv=argv, stdout=cold_stdout, stderr=cold_stderr)
    warm_exit: int = run_check(argv=argv, stdout=warm_stdout, stderr=warm_stderr)

    assert cold_exit == test_case.expected_exit_code
    assert warm_exit == test_case.expected_exit_code
    assert warm_stdout.getvalue() == cold_stdout.getvalue()
    assert test_case.expected_fault_fragment in cold_stdout.getvalue()
    assert test_case.expected_summary_fragment in cold_stdout.getvalue()
    assert test_case.expected_cold_stats_fragment in cold_stderr.getvalue()
    assert test_case.expected_warm_stats_fragment in warm_stderr.getvalue()
    assert test_case.expected_non_cacheable_fragment in cold_stderr.getvalue()
    assert test_case.expected_non_cacheable_fragment in warm_stderr.getvalue()


@pytest.mark.parametrize(
    "test_case",
    [
        NestedContainerCacheTestCase(
            description="role bucket initializer ownership remains fully cacheable",
            expected_exit_code=1,
            expected_fault_fragment="SFR301  _helpers/ bucket 'main/' uses a runtime role name",
            expected_summary_fragment="Found 1 fault",
            expected_cold_stats_fragment="hits=0 misses=2",
            expected_warm_stats_fragment="hits=2 misses=0",
            expected_non_cacheable_fragment="non_cacheable=0",
        )
    ],
    ids=lambda case: case.description,
)
def test_given_initialized_role_bucket_when_running_cold_and_warm_then_reuses_owner_result(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    test_case: NestedContainerCacheTestCase,
) -> None:
    (tmp_path / "strata.toml").write_text(
        'roots = ["src/pkg"]\nselect = ["SFR301"]\n[thresholds]\nmax_role_depth = 2\n',
        encoding="utf-8",
    )
    bucket: Path = tmp_path / "src/pkg/orders/_helpers/main"
    descendant: Path = bucket / "parsing/read.py"
    descendant.parent.mkdir(parents=True)
    (bucket / "__init__.py").write_text("", encoding="utf-8")
    descendant.write_text("", encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    cold_stdout: CaptureOutput = CaptureOutput()
    cold_stderr: CaptureOutput = CaptureOutput()
    warm_stdout: CaptureOutput = CaptureOutput()
    warm_stderr: CaptureOutput = CaptureOutput()
    argv: tuple[str, ...] = ("--no-color", "--cache", "--cache-stats")

    cold_exit: int = run_check(argv=argv, stdout=cold_stdout, stderr=cold_stderr)
    warm_exit: int = run_check(argv=argv, stdout=warm_stdout, stderr=warm_stderr)

    assert cold_exit == test_case.expected_exit_code
    assert warm_exit == test_case.expected_exit_code
    assert warm_stdout.getvalue() == cold_stdout.getvalue()
    assert test_case.expected_fault_fragment in cold_stdout.getvalue()
    assert test_case.expected_summary_fragment in cold_stdout.getvalue()
    assert test_case.expected_cold_stats_fragment in cold_stderr.getvalue()
    assert test_case.expected_warm_stats_fragment in warm_stderr.getvalue()
    assert test_case.expected_non_cacheable_fragment in cold_stderr.getvalue()
    assert test_case.expected_non_cacheable_fragment in warm_stderr.getvalue()


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
        CheckNoFaultTestCase(
            description="file-level exception survives cold and warm checks",
            argv=("--no-color", "--cache"),
            expected_exit_code=0,
            expected_output_fragment="Found 0 faults\nApplied 1 rule exception",
        )
    ],
    ids=lambda case: case.description,
)
def test_given_file_level_exception_when_running_check_then_suppresses_path_fault(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    test_case: CheckNoFaultTestCase,
) -> None:
    write_cli_file_exception_project(tmp_path)
    monkeypatch.chdir(tmp_path)
    cold_stdout: CaptureOutput = CaptureOutput()
    warm_stdout: CaptureOutput = CaptureOutput()

    cold_exit: int = run_check(argv=test_case.argv, stdout=cold_stdout)
    warm_exit: int = run_check(argv=test_case.argv, stdout=warm_stdout)

    assert cold_exit == test_case.expected_exit_code
    assert warm_exit == test_case.expected_exit_code
    assert test_case.expected_output_fragment in cold_stdout.getvalue()
    assert warm_stdout.getvalue() == cold_stdout.getvalue()


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
        CheckCachePreferenceTestCase(
            description="configured default enables cache without a CLI flag",
            configured_enabled=True,
            argv=("--no-color",),
            expected_exit_code=1,
            expected_cache_exists=True,
        ),
        CheckCachePreferenceTestCase(
            description="configured preference disables cache without a CLI flag",
            configured_enabled=False,
            argv=("--no-color",),
            expected_exit_code=1,
            expected_cache_exists=False,
        ),
        CheckCachePreferenceTestCase(
            description="cache flag overrides disabled configured preference",
            configured_enabled=False,
            argv=("--no-color", "--cache"),
            expected_exit_code=1,
            expected_cache_exists=True,
        ),
        CheckCachePreferenceTestCase(
            description="no-cache flag overrides enabled configured preference",
            configured_enabled=True,
            argv=("--no-color", "--no-cache"),
            expected_exit_code=1,
            expected_cache_exists=False,
        ),
    ],
    ids=lambda case: case.description,
)
def test_given_cache_preference_when_running_check_then_cli_override_has_precedence(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    test_case: CheckCachePreferenceTestCase,
) -> None:
    write_cli_core_fault_project(tmp_path, cache_enabled=test_case.configured_enabled)
    monkeypatch.chdir(tmp_path)
    stdout: CaptureOutput = CaptureOutput()

    exit_code: int = run_check(argv=test_case.argv, stdout=stdout)

    assert exit_code == test_case.expected_exit_code
    assert (tmp_path / CACHE_DATABASE_RELATIVE_PATH).exists() is test_case.expected_cache_exists


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
