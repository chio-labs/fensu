"""Tests for `strata check` orchestration."""

from __future__ import annotations

from pathlib import Path

import pytest

from strata.agentdocs._helpers import freshness
from strata.agentdocs.main import check_install
from strata.cache.fingerprints.models import GlobalFingerprintBuild
from strata.cache.results.classes.result_cache import ResultCache
from strata.cache.results.models import CacheStats
from strata.cache.storage.constants import CACHE_DATABASE_RELATIVE_PATH
from strata.cache.storage.exceptions import CacheRecordError
from strata.cli.main._skills import run_skills
from strata.cli.main.check import run_check
from strata.instrumentation.constants import (
    EVALUATION_WORKER_PARTITION_OPERATION,
    OPERATION_COUNTERS,
)
from tests.integration.src.strata.cli.main._test_types import (
    CacheableNoticeTestCase,
    CheckCacheModeTestCase,
    CheckCachePreferenceTestCase,
    CheckCacheWarningTestCase,
    CheckCommandTestCase,
    CheckErrorTestCase,
    CheckFooterTestCase,
    CheckNoFaultTestCase,
    CheckSkillFreshnessTestCase,
    EvaluationCheckTestCase,
    MemoryCheckIntegrationTestCase,
    MixedRulesetCacheTestCase,
    NestedContainerCacheTestCase,
    ParallelCheckTestCase,
    ReplayFastPathTestCase,
    ScopedCacheWarningTestCase,
    ShortCircuitCheckTestCase,
    ThresholdOverrideCheckTestCase,
    WarningCacheIdentityTestCase,
    WarningCheckTestCase,
)
from tests.integration.src.strata.cli.main.helpers import (
    CallCounter,
    CaptureOutput,
    RestoreProbe,
    SkillReadCounter,
    cache_snapshot,
    counting_plan_native_generation,
    fail_skill_renderer,
    mutate_skill_freshness_state,
    prepare_normal_check_skill_state,
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
            expected_evaluation_footer=("Evaluation: 1 of 2 Python files (1 excluded by config)\n"),
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
    assert test_case.expected_evaluation_footer in cached_stdout.getvalue()
    assert cached_stdout.getvalue().endswith(test_case.expected_evaluation_footer)
    assert test_case.expected_fault_fragment in cached_stdout.getvalue()
    assert test_case.expected_absent_fragment not in cached_stdout.getvalue()


@pytest.mark.parametrize(
    "test_case",
    [
        ParallelCheckTestCase(
            description="parallel no-cache workers produce byte-identical reporting",
            jobs="2",
            cache_flag="--no-cache",
            expected_exit_code=1,
            expected_fault_fragments=("src/pkg/alpha.py", "src/pkg/gamma.py"),
            expected_cache_exists=False,
            expected_cache_stats_fragment="",
            expected_worker_partitions=1,
        ),
        ParallelCheckTestCase(
            description="parallel cold-cache workers publish byte-identical reporting",
            jobs="2",
            cache_flag="--cache",
            expected_exit_code=1,
            expected_fault_fragments=("src/pkg/alpha.py", "src/pkg/gamma.py"),
            expected_cache_exists=True,
            expected_cache_stats_fragment="hits=0 misses=3 invalidations=0 writes=3",
            expected_worker_partitions=1,
        ),
    ],
    ids=lambda case: case.description,
)
def test_given_parallel_jobs_when_running_check_then_matches_serial_output(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    test_case: ParallelCheckTestCase,
) -> None:
    (tmp_path / "strata.toml").write_text(
        'roots = ["src/pkg"]\ntests = []\nselect = ["SFA101"]\n',
        encoding="utf-8",
    )
    package: Path = tmp_path / "src/pkg"
    package.mkdir(parents=True)
    (package / "alpha.py").write_text("ALPHA = 1\n", encoding="utf-8")
    (package / "beta.py").write_text("BETA: int = 1\n", encoding="utf-8")
    (package / "gamma.py").write_text("GAMMA = 1\n", encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    serial_stdout: CaptureOutput = CaptureOutput()
    parallel_stdout: CaptureOutput = CaptureOutput()
    parallel_stderr: CaptureOutput = CaptureOutput()

    serial_exit: int = run_check(
        argv=("--no-color", "--no-cache"), stdout=serial_stdout, stderr=CaptureOutput()
    )
    OPERATION_COUNTERS.enable()
    parallel_exit: int = run_check(
        argv=(
            "--no-color",
            test_case.cache_flag,
            "--cache-stats",
            "--jobs",
            test_case.jobs,
        ),
        stdout=parallel_stdout,
        stderr=parallel_stderr,
    )
    operation_counts: dict[str, int] = OPERATION_COUNTERS.snapshot()
    OPERATION_COUNTERS.disable()

    assert serial_exit == test_case.expected_exit_code
    assert parallel_exit == test_case.expected_exit_code
    assert parallel_stdout.getvalue() == serial_stdout.getvalue()
    for fragment in test_case.expected_fault_fragments:
        assert fragment in parallel_stdout.getvalue()
    assert (tmp_path / CACHE_DATABASE_RELATIVE_PATH).exists() is test_case.expected_cache_exists
    assert test_case.expected_cache_stats_fragment in parallel_stderr.getvalue()
    assert (
        operation_counts.get(EVALUATION_WORKER_PARTITION_OPERATION, 0)
        == test_case.expected_worker_partitions
    )


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
        WarningCheckTestCase(
            description="plain check does not evaluate configured warning rule",
            source="def build():\n    return 1\n",
            argv=("--no-color", "--no-cache"),
            expected_exit_code=0,
            expected_summary="Found 0 faults",
            expected_warning_count=0,
            expected_fault_count=0,
        ),
        WarningCheckTestCase(
            description="warning check reports zero warnings with explicit grammar",
            source="def build() -> int:\n    return 1\n",
            argv=("--no-color", "--no-cache", "--warn"),
            expected_exit_code=0,
            expected_summary="Found 0 faults and 0 warnings",
            expected_warning_count=0,
            expected_fault_count=0,
        ),
        WarningCheckTestCase(
            description="warning-only finding succeeds with singular grammar",
            source="def build():\n    return 1\n",
            argv=("--no-color", "--no-cache", "--warn"),
            expected_exit_code=0,
            expected_summary="Found 0 faults and 1 warning",
            expected_warning_count=1,
            expected_fault_count=0,
        ),
        WarningCheckTestCase(
            description="multiple warning findings succeed with plural grammar",
            source="def build():\n    return 1\ndef load():\n    return 2\n",
            argv=("--no-color", "--no-cache", "--warn"),
            expected_exit_code=0,
            expected_summary="Found 0 faults and 2 warnings",
            expected_warning_count=2,
            expected_fault_count=0,
        ),
        WarningCheckTestCase(
            description="mixed blocking and warning findings fail only for the blocking fault",
            source="VALUE = 1\ndef build():\n    return 1\n",
            argv=("--no-color", "--no-cache", "--warn"),
            expected_exit_code=1,
            expected_summary="Found 1 fault and 1 warning",
            expected_warning_count=1,
            expected_fault_count=1,
        ),
    ],
    ids=lambda case: case.description,
)
def test_given_configured_warning_rules_when_running_check_then_evaluates_only_requested_tiers(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    test_case: WarningCheckTestCase,
) -> None:
    (tmp_path / "strata.toml").write_text(
        'roots = ["src/pkg"]\ntests = []\nselect = ["SFA101"]\nwarn = ["SFA002"]\n',
        encoding="utf-8",
    )
    source: Path = tmp_path / "src/pkg/module.py"
    source.parent.mkdir(parents=True)
    source.write_text(test_case.source, encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    stdout: CaptureOutput = CaptureOutput()

    exit_code: int = run_check(argv=test_case.argv, stdout=stdout)

    output: str = stdout.getvalue()
    assert exit_code == test_case.expected_exit_code
    assert test_case.expected_summary in output
    assert output.count("SFA002  ") == test_case.expected_warning_count
    assert output.count("SFA101  ") == test_case.expected_fault_count
    assert output.count("= warning:") == test_case.expected_warning_count


@pytest.mark.parametrize(
    "test_case",
    [
        WarningCacheIdentityTestCase(
            description="plain to warning mode switches miss before warning mode warms",
            first_argv=("--no-color", "--cache", "--cache-stats"),
            second_argv=("--no-color", "--cache", "--cache-stats", "--warn"),
            third_argv=("--no-color", "--cache", "--cache-stats", "--warn"),
            expected_switch_stats="hits=0 misses=1",
            expected_warm_stats="hits=1 misses=0",
        ),
        WarningCacheIdentityTestCase(
            description="warning to plain mode switches miss before plain mode warms",
            first_argv=("--no-color", "--cache", "--cache-stats", "--warn"),
            second_argv=("--no-color", "--cache", "--cache-stats"),
            third_argv=("--no-color", "--cache", "--cache-stats"),
            expected_switch_stats="hits=0 misses=1",
            expected_warm_stats="hits=1 misses=0",
        ),
    ],
    ids=lambda case: case.description,
)
def test_given_cached_warning_mode_switch_when_running_check_then_uses_distinct_identity(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    test_case: WarningCacheIdentityTestCase,
) -> None:
    (tmp_path / "strata.toml").write_text(
        'roots = ["src/pkg"]\ntests = []\nselect = ["SFA101"]\nwarn = ["SFA002"]\n',
        encoding="utf-8",
    )
    source: Path = tmp_path / "src/pkg/module.py"
    source.parent.mkdir(parents=True)
    source.write_text("def build():\n    return 1\n", encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    first_stderr: CaptureOutput = CaptureOutput()
    second_stderr: CaptureOutput = CaptureOutput()
    third_stderr: CaptureOutput = CaptureOutput()

    _ = run_check(argv=test_case.first_argv, stdout=CaptureOutput(), stderr=first_stderr)
    _ = run_check(argv=test_case.second_argv, stdout=CaptureOutput(), stderr=second_stderr)
    _ = run_check(argv=test_case.third_argv, stdout=CaptureOutput(), stderr=third_stderr)

    assert test_case.expected_switch_stats in first_stderr.getvalue()
    assert test_case.expected_switch_stats in second_stderr.getvalue()
    assert test_case.expected_warm_stats in third_stderr.getvalue()


@pytest.mark.parametrize(
    "test_case",
    [
        ScopedCacheWarningTestCase(
            description="warn-only uncacheable custom rule keeps both modes cache-eligible",
            argv=("--no-color", "--cache", "--cache-stats", "--warn"),
            expected_exit_code=0,
            expected_output_fragment="Found 0 faults and 1 warning",
            expected_cold_stats="hits=0 misses=1",
            expected_warm_stats="hits=1 misses=0",
        )
    ],
    ids=lambda case: case.description,
)
def test_given_warn_only_uncacheable_custom_rule_when_switching_modes_then_plain_cache_remains_eligible(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    test_case: ScopedCacheWarningTestCase,
) -> None:
    (tmp_path / "strata.toml").write_text(
        'roots = ["src/pkg"]\ntests = []\nselect = ["SFA101"]\nwarn = ["XWC001"]\n'
        'rule_paths = ["rules/custom.py"]\n',
        encoding="utf-8",
    )
    source: Path = tmp_path / "src/pkg/module.py"
    source.parent.mkdir(parents=True)
    source.write_text("VALUE: int = 1\n", encoding="utf-8")
    custom_rule: Path = tmp_path / "rules/custom.py"
    custom_rule.parent.mkdir()
    custom_rule.write_text(
        "from __future__ import annotations\n"
        "import ast\n"
        "from strata import Family, Fault, RuleContext, rule\n"
        "@rule(code='XWC001', family=Family.CUSTOM, slug='warning', message='review')\n"
        "def warning(module: ast.Module, ctx: RuleContext) -> list[Fault]:\n"
        "    return [ctx.fault(node=module.body[0])]\n",
        encoding="utf-8",
    )
    monkeypatch.chdir(tmp_path)
    plain_cold_stderr: CaptureOutput = CaptureOutput()
    plain_warm_stderr: CaptureOutput = CaptureOutput()
    warned_cold_stdout: CaptureOutput = CaptureOutput()
    warned_cold_stderr: CaptureOutput = CaptureOutput()
    warned_warm_stdout: CaptureOutput = CaptureOutput()
    warned_warm_stderr: CaptureOutput = CaptureOutput()
    plain_argv: tuple[str, ...] = ("--no-color", "--cache", "--cache-stats")

    _ = run_check(argv=plain_argv, stdout=CaptureOutput(), stderr=plain_cold_stderr)
    _ = run_check(argv=plain_argv, stdout=CaptureOutput(), stderr=plain_warm_stderr)
    warned_cold_exit: int = run_check(
        argv=test_case.argv,
        stdout=warned_cold_stdout,
        stderr=warned_cold_stderr,
    )
    warned_warm_exit: int = run_check(
        argv=test_case.argv,
        stdout=warned_warm_stdout,
        stderr=warned_warm_stderr,
    )

    assert test_case.expected_cold_stats in plain_cold_stderr.getvalue()
    assert test_case.expected_warm_stats in plain_warm_stderr.getvalue()
    assert warned_cold_exit == test_case.expected_exit_code
    assert warned_warm_exit == test_case.expected_exit_code
    assert test_case.expected_output_fragment in warned_cold_stdout.getvalue()
    assert test_case.expected_cold_stats in warned_cold_stderr.getvalue()
    assert test_case.expected_warm_stats in warned_warm_stderr.getvalue()
    assert warned_warm_stdout.getvalue() == warned_cold_stdout.getvalue()


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

    monkeypatch.setattr(
        "strata.cli._helpers.check_evaluation.build_global_fingerprint", fail_fingerprint
    )

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

    monkeypatch.setattr(ResultCache, "publish_native_generation", raise_publish)

    exit_code: int = run_check(argv=test_case.argv, stdout=stdout, stderr=stderr)

    assert exit_code == test_case.expected_exit_code
    assert test_case.expected_output_fragment in stdout.getvalue()
    assert test_case.expected_warning_fragment in stderr.getvalue()


@pytest.mark.parametrize(
    "test_case",
    [
        CheckSkillFreshnessTestCase(
            description="declined installation does not create a permanent missing warning",
            state="declined",
            expected_exit_code=1,
            expected_warning_count=0,
        ),
        CheckSkillFreshnessTestCase(
            description="unmanaged local skill is outside automatic freshness ownership",
            state="unmanaged",
            expected_exit_code=1,
            expected_warning_count=0,
        ),
        CheckSkillFreshnessTestCase(
            description="malformed marker is left to authoritative update check",
            state="malformed-marker",
            expected_exit_code=1,
            expected_warning_count=0,
        ),
        CheckSkillFreshnessTestCase(
            description="current owned skill ignores invocation root and cache overrides",
            state="current",
            expected_exit_code=1,
            expected_warning_count=0,
        ),
        CheckSkillFreshnessTestCase(
            description="manual divergence warns without changing fault exit status",
            state="divergent",
            expected_exit_code=1,
            expected_warning_count=1,
        ),
        CheckSkillFreshnessTestCase(
            description="three stale default targets produce one warning",
            state="stale-all",
            expected_exit_code=1,
            expected_warning_count=1,
        ),
    ],
    ids=lambda case: case.description,
)
def test_given_default_local_skill_state_when_checking_then_warns_only_for_owned_staleness(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    test_case: CheckSkillFreshnessTestCase,
) -> None:
    write_cli_fixture_project(root=tmp_path, rule_code="XCF001")
    monkeypatch.chdir(tmp_path)
    prepare_normal_check_skill_state(root=tmp_path, state=test_case.state)
    stdout: CaptureOutput = CaptureOutput()
    stderr: CaptureOutput = CaptureOutput()

    exit_code: int = run_check(
        argv=("--no-color", "--no-cache", "src/pkg"),
        stdout=stdout,
        stderr=stderr,
    )
    warning: str = "Strata skill files are out of date"

    assert exit_code == test_case.expected_exit_code
    assert "Found 1 fault" in stdout.getvalue()
    assert stderr.getvalue().count(warning) == test_case.expected_warning_count


@pytest.mark.parametrize(
    "test_case",
    [
        CheckNoFaultTestCase(
            description="stale skill warning never makes a clean check fail",
            argv=("--no-color", "--no-cache"),
            expected_exit_code=0,
            expected_output_fragment="Found 0 faults",
        )
    ],
    ids=lambda case: case.description,
)
def test_given_clean_project_and_divergent_owned_skill_when_checking_then_exit_remains_zero(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    test_case: CheckNoFaultTestCase,
) -> None:
    source: Path = tmp_path / "src/pkg/domain/constants.py"
    source.parent.mkdir(parents=True)
    source.write_text("VALUE: int = 1\n", encoding="utf-8")
    (tmp_path / "strata.toml").write_text(
        'roots = ["src/pkg"]\ntests = []\nselect = ["SFA001"]\n[skills]\nname = "fixture"\n',
        encoding="utf-8",
    )
    monkeypatch.chdir(tmp_path)
    installed: int = run_skills(argv=("--target", "agents"))
    mutate_skill_freshness_state(root=tmp_path, state="divergent")
    stdout: CaptureOutput = CaptureOutput()
    stderr: CaptureOutput = CaptureOutput()

    exit_code: int = run_check(argv=test_case.argv, stdout=stdout, stderr=stderr)

    assert installed == 0
    assert exit_code == test_case.expected_exit_code
    assert test_case.expected_output_fragment in stdout.getvalue()
    assert "Strata skill files are out of date" in stderr.getvalue()


@pytest.mark.parametrize(
    "test_case",
    [
        CheckFooterTestCase(
            description="filtered exception check ends with actionable styled skill notice",
            expected_exit_code=0,
            expected_output=(
                "\033[1;32mFound 0 faults\033[0m\n"
                "\033[2mEvaluation: 1 of 2 Python files (1 excluded by config)\033[0m\n"
                "Applied 1 rule exception\n"
                "\n\033[1;38;5;208mStrata skill files are out of date\033[0m\n"
                "  Run: \033[1;36mstrata skills\033[0m\n"
            ),
        )
    ],
    ids=lambda case: case.description,
)
def test_given_stale_skill_and_filtered_exception_when_checking_then_orders_footer_actions(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    test_case: CheckFooterTestCase,
) -> None:
    write_cli_exception_project(tmp_path)
    config: Path = tmp_path / "strata.toml"
    config.write_text(
        config.read_text(encoding="utf-8")
        + '\n[evaluation]\ninclude = ["src/pkg/external.py"]\n'
        + '[skills]\nname = "fixture"\n',
        encoding="utf-8",
    )
    excluded: Path = tmp_path / "src/pkg/excluded.py"
    excluded.write_text("VALUE: int = 1\n", encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    installed: int = run_skills(argv=("--target", "agents"))
    mutate_skill_freshness_state(root=tmp_path, state="divergent")
    output: CaptureOutput = CaptureOutput(is_terminal=True)

    exit_code: int = run_check(argv=("--no-cache",), stdout=output, stderr=output)

    assert installed == 0
    assert exit_code == test_case.expected_exit_code
    assert output.getvalue() == test_case.expected_output


@pytest.mark.parametrize(
    "test_case",
    [
        CheckSkillFreshnessTestCase(
            description="normal freshness performs three probes and zero Markdown renders",
            state="current",
            expected_exit_code=1,
            expected_warning_count=0,
        )
    ],
    ids=lambda case: case.description,
)
def test_given_current_owned_skill_when_checking_then_uses_bounded_renderer_free_fast_path(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    test_case: CheckSkillFreshnessTestCase,
) -> None:
    write_cli_fixture_project(root=tmp_path, rule_code="XFP001")
    monkeypatch.chdir(tmp_path)
    installed: int = run_skills(argv=("--target", "agents"))
    reader: SkillReadCounter = SkillReadCounter(freshness._read_skill_content)
    monkeypatch.setattr(freshness, "_read_skill_content", reader)
    monkeypatch.setattr(check_install, "generate_skill", fail_skill_renderer)
    stderr: CaptureOutput = CaptureOutput()

    exit_code: int = run_check(
        argv=("--no-color", "--no-cache"),
        stdout=CaptureOutput(),
        stderr=stderr,
    )

    assert installed == 0
    assert exit_code == test_case.expected_exit_code
    assert reader.calls == 3
    assert stderr.getvalue().count("Strata skill files are out of date") == (
        test_case.expected_warning_count
    )


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
        "strata.cli._helpers.check_evaluation.build_global_fingerprint",
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
        "strata.cli._helpers.check_evaluation.build_global_fingerprint",
        lambda **kwargs: GlobalFingerprintBuild(
            fingerprint=None,
            disabled_reason="the loaded implementation files are unavailable",
        ),
    )

    exit_code: int = run_check(argv=test_case.argv, stdout=stdout, stderr=stderr)

    assert exit_code == test_case.expected_exit_code
    assert test_case.expected_output_fragment in stdout.getvalue()
    assert test_case.expected_warning_fragment in stderr.getvalue()


@pytest.mark.parametrize(
    "test_case",
    [
        ShortCircuitCheckTestCase(
            description="unchanged warm run emits stored output without restoring records",
            expected_exit_code=1,
            expected_warm_restores=0,
            expected_edited_restores=0,
            expected_edited_fragment="module-level variable 'EXTRA'",
        )
    ],
    ids=lambda case: case.description,
)
def test_given_unchanged_tree_when_rechecking_then_short_circuits_stored_output(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    test_case: ShortCircuitCheckTestCase,
) -> None:
    (tmp_path / "strata.toml").write_text(
        'roots = ["src/pkg"]\ntests = []\nselect = ["SFA101"]\n',
        encoding="utf-8",
    )
    package: Path = tmp_path / "src/pkg"
    package.mkdir(parents=True)
    (package / "faulty.py").write_text("TARGET = 1\n", encoding="utf-8")
    (package / "clean.py").write_text("CLEAN: int = 1\n", encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    probe: RestoreProbe = RestoreProbe()
    monkeypatch.setattr("strata.cache.results._helpers.conversion.restore_native_evaluation", probe)
    cold_stdout: CaptureOutput = CaptureOutput()
    warm_stdout: CaptureOutput = CaptureOutput()
    edited_stdout: CaptureOutput = CaptureOutput()

    cold_exit: int = run_check(
        argv=("--no-color", "--cache"), stdout=cold_stdout, stderr=CaptureOutput()
    )
    warm_exit: int = run_check(
        argv=("--no-color", "--cache"), stdout=warm_stdout, stderr=CaptureOutput()
    )
    warm_restores: int = probe.calls
    (package / "faulty.py").write_text("TARGET = 1\nEXTRA = 2\n", encoding="utf-8")
    edited_exit: int = run_check(
        argv=("--no-color", "--cache"), stdout=edited_stdout, stderr=CaptureOutput()
    )

    assert cold_exit == test_case.expected_exit_code
    assert warm_exit == test_case.expected_exit_code
    assert edited_exit == test_case.expected_exit_code
    assert warm_stdout.getvalue() == cold_stdout.getvalue()
    assert warm_restores == test_case.expected_warm_restores
    assert probe.calls - warm_restores == test_case.expected_edited_restores
    assert test_case.expected_edited_fragment in edited_stdout.getvalue()


@pytest.mark.parametrize(
    "test_case",
    [
        ReplayFastPathTestCase(
            description="warm and edited runs replay observations without reading records",
            expected_exit_code=1,
            expected_warm_loads=0,
            expected_edited_loads=1,
            expected_warm_context_loads=0,
        )
    ],
    ids=lambda case: case.description,
)
def test_given_unchanged_tree_when_rechecking_then_skips_record_loads(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    test_case: ReplayFastPathTestCase,
) -> None:
    (tmp_path / "strata.toml").write_text(
        'roots = ["src/pkg"]\ntests = []\nselect = ["SFA101"]\n',
        encoding="utf-8",
    )
    package: Path = tmp_path / "src/pkg"
    package.mkdir(parents=True)
    (package / "faulty.py").write_text("TARGET = 1\n", encoding="utf-8")
    (package / "clean.py").write_text("CLEAN: int = 1\n", encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    counter: CallCounter = CallCounter()
    monkeypatch.setattr(
        "strata.cache.results.classes.result_cache.ResultCache.plan_native_generation",
        counting_plan_native_generation(counter),
    )
    cold_stdout: CaptureOutput = CaptureOutput()
    warm_stdout: CaptureOutput = CaptureOutput()

    cold_exit: int = run_check(
        argv=("--no-color", "--cache"), stdout=cold_stdout, stderr=CaptureOutput()
    )
    cold_loads: int = counter.calls
    warm_exit: int = run_check(
        argv=("--no-color", "--cache"), stdout=warm_stdout, stderr=CaptureOutput()
    )
    warm_loads: int = counter.calls - cold_loads
    (package / "faulty.py").write_text("TARGET = 1\nEXTRA = 2\n", encoding="utf-8")
    edited_exit: int = run_check(
        argv=("--no-color", "--cache"), stdout=CaptureOutput(), stderr=CaptureOutput()
    )

    assert cold_exit == test_case.expected_exit_code
    assert warm_exit == test_case.expected_exit_code
    assert edited_exit == test_case.expected_exit_code
    assert warm_stdout.getvalue() == cold_stdout.getvalue()
    assert warm_loads == test_case.expected_warm_loads
    assert counter.calls - cold_loads - warm_loads == test_case.expected_edited_loads


@pytest.mark.parametrize(
    "test_case",
    [
        MixedRulesetCacheTestCase(
            description="mixed ruleset caches core rules and re-runs the custom rule fresh",
            argv=("--no-color", "--cache", "--cache-stats"),
            expected_exit_code=1,
            expected_custom_fragment="XSC001",
            expected_core_fragment="SFA101",
            expected_cold_stats="hits=0 misses=1",
            expected_warm_stats="hits=1 misses=0 invalidations=0 writes=0",
        )
    ],
    ids=lambda case: case.description,
)
def test_given_mixed_ruleset_when_rechecking_then_scopes_cache_to_cacheable_rules(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    test_case: MixedRulesetCacheTestCase,
) -> None:
    (tmp_path / "strata.toml").write_text(
        'roots = ["src/pkg"]\ntests = []\nselect = ["SFA101", "XSC001"]\n'
        'rule_paths = ["rules/custom.py"]\n',
        encoding="utf-8",
    )
    source: Path = tmp_path / "src/pkg/module.py"
    source.parent.mkdir(parents=True)
    source.write_text("VALUE = 1\n", encoding="utf-8")
    custom_rule: Path = tmp_path / "rules/custom.py"
    custom_rule.parent.mkdir()
    custom_rule.write_text(
        "from __future__ import annotations\n"
        "import ast\n"
        "from strata import Family, Fault, RuleContext, rule\n"
        "@rule(code='XSC001', family=Family.CUSTOM, slug='scoped', message='scoped fault')\n"
        "def scoped(module: ast.Module, ctx: RuleContext) -> list[Fault]:\n"
        "    return [ctx.fault(node=module.body[0])]\n",
        encoding="utf-8",
    )
    monkeypatch.chdir(tmp_path)
    uncached_stdout: CaptureOutput = CaptureOutput()
    cold_stdout: CaptureOutput = CaptureOutput()
    cold_stderr: CaptureOutput = CaptureOutput()
    warm_stdout: CaptureOutput = CaptureOutput()
    warm_stderr: CaptureOutput = CaptureOutput()

    uncached_exit: int = run_check(
        argv=("--no-color", "--no-cache"), stdout=uncached_stdout, stderr=CaptureOutput()
    )
    cold_exit: int = run_check(argv=test_case.argv, stdout=cold_stdout, stderr=cold_stderr)
    warm_exit: int = run_check(argv=test_case.argv, stdout=warm_stdout, stderr=warm_stderr)
    records: tuple[tuple[str, bytes], ...] = cache_snapshot(tmp_path)

    assert uncached_exit == test_case.expected_exit_code
    assert cold_exit == test_case.expected_exit_code
    assert warm_exit == test_case.expected_exit_code
    assert test_case.expected_custom_fragment in cold_stdout.getvalue()
    assert test_case.expected_core_fragment in cold_stdout.getvalue()
    assert cold_stdout.getvalue() == uncached_stdout.getvalue()
    assert warm_stdout.getvalue() == uncached_stdout.getvalue()
    assert test_case.expected_cold_stats in cold_stderr.getvalue()
    assert test_case.expected_warm_stats in warm_stderr.getvalue()
    assert records
    assert all(
        test_case.expected_custom_fragment.encode("utf-8") not in data for _, data in records
    )
    assert all(b'"kind":"check_output"' not in data for _, data in records)


@pytest.mark.parametrize(
    "test_case",
    [
        CacheableNoticeTestCase(
            description="undeclared hermetic custom rule earns a one-line notice",
            decorator_arguments="",
            argv=("--no-color", "--cache"),
            expected_exit_code=1,
            expected_notice=True,
        ),
        CacheableNoticeTestCase(
            description="declared promise silences the notice",
            decorator_arguments=", cacheable=True",
            argv=("--no-color", "--cache"),
            expected_exit_code=1,
            expected_notice=False,
        ),
        CacheableNoticeTestCase(
            description="declared opt-out silences the notice",
            decorator_arguments=", cacheable=False",
            argv=("--no-color", "--cache"),
            expected_exit_code=1,
            expected_notice=False,
        ),
        CacheableNoticeTestCase(
            description="uncached runs never emit the notice",
            decorator_arguments="",
            argv=("--no-color", "--no-cache"),
            expected_exit_code=1,
            expected_notice=False,
        ),
    ],
    ids=lambda case: case.description,
)
def test_given_custom_rule_declaration_when_checking_then_reports_cacheable_notice(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    test_case: CacheableNoticeTestCase,
) -> None:
    (tmp_path / "strata.toml").write_text(
        'roots = ["src/pkg"]\ntests = []\nselect = ["SFA101", "XNC001"]\n'
        'rule_paths = ["rules/custom.py"]\n',
        encoding="utf-8",
    )
    source: Path = tmp_path / "src/pkg/module.py"
    source.parent.mkdir(parents=True)
    source.write_text("VALUE: int = 1\n", encoding="utf-8")
    custom_rule: Path = tmp_path / "rules/custom.py"
    custom_rule.parent.mkdir()
    custom_rule.write_text(
        "from __future__ import annotations\n"
        "import ast\n"
        "from strata import Family, Fault, RuleContext, rule\n"
        "@rule(code='XNC001', family=Family.CUSTOM, slug='notice', message='notice fault'"
        f"{test_case.decorator_arguments})\n"
        "def notice(module: ast.Module, ctx: RuleContext) -> list[Fault]:\n"
        "    return [ctx.fault(node=module.body[0])]\n",
        encoding="utf-8",
    )
    monkeypatch.chdir(tmp_path)
    stdout: CaptureOutput = CaptureOutput()
    stderr: CaptureOutput = CaptureOutput()

    exit_code: int = run_check(argv=test_case.argv, stdout=stdout, stderr=stderr)

    assert exit_code == test_case.expected_exit_code
    assert "XNC001" in stdout.getvalue()
    notice_present: bool = (
        "Custom rules appear cacheable; declare cacheable=True" in stderr.getvalue()
    )
    assert notice_present is test_case.expected_notice


@pytest.mark.parametrize(
    "test_case",
    [
        MemoryCheckIntegrationTestCase(
            description="enabled memory findings append after clean architecture diagnostics",
            expected_exit_code=1,
            expected_memory_fault="MEM002",
            expected_architecture_summary="Found 0 faults",
            expected_memory_summary="Found 1 fault",
        )
    ],
    ids=lambda case: case.description,
)
def test_given_enabled_invalid_memory_when_running_check_then_reports_memory_after_architecture(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    test_case: MemoryCheckIntegrationTestCase,
) -> None:
    (tmp_path / "strata.toml").write_text(
        'roots = ["src/pkg"]\ntests = []\nselect = ["SFA101"]\n[experimental]\nmemory = true\n',
        encoding="utf-8",
    )
    source: Path = tmp_path / "src/pkg/module.py"
    source.parent.mkdir(parents=True)
    source.write_text("VALUE: int = 1\n", encoding="utf-8")
    memory_source: Path = tmp_path / ".ai/orphan.md"
    memory_source.parent.mkdir()
    memory_source.write_text("# Orphan\n", encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    stdout: CaptureOutput = CaptureOutput()

    exit_code: int = run_check(
        argv=("--no-color", "--cache"),
        stdout=stdout,
        stderr=CaptureOutput(),
    )

    output: str = stdout.getvalue()
    assert exit_code == test_case.expected_exit_code
    assert test_case.expected_memory_fault in output
    assert test_case.expected_architecture_summary in output
    assert test_case.expected_memory_summary in output
