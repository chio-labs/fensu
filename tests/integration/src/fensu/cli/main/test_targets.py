"""Tests for named targets in the Python custom-rule check host."""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

import pytest

import fensu.cli._helpers.check_setup as check_setup_module
from fensu.cache.results.classes.result_cache import ResultCache
from fensu.cache.results.models import CacheStats
from fensu.cli.main.custom_check_host import run_custom_check as run_check
from tests.integration.src.fensu.cli.main._test_types import (
    AggregateAnalyzerPreflightTestCase,
    CanonicalAliasCheckTestCase,
    MultiTargetCacheCheckTestCase,
    MultiTargetThresholdOrderTestCase,
    TargetCheckTestCase,
    UnavailableAnalyzerHostTestCase,
)
from tests.integration.src.fensu.cli.main.helpers import (
    CaptureOutput,
    run_custom_check_process,
    write_cacheability_advice_target_project,
    write_cacheable_target_project,
    write_mixed_cacheability_target_project,
)


@pytest.mark.parametrize(
    "test_case",
    [
        UnavailableAnalyzerHostTestCase(
            description=f"known {analyzer} target fails before Python discovery",
            analyzer=analyzer,
            expected_exit_code=2,
            expected_error_fragment=f"Known analyzer backend unavailable: {analyzer}",
        )
        for analyzer in ("typescript", "svelte")
    ],
    ids=lambda case: case.description,
)
def test_given_known_unavailable_target_when_running_python_host_then_fails_before_discovery(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    test_case: UnavailableAnalyzerHostTestCase,
) -> None:
    marker: Path = tmp_path / "custom-rule-imported"
    (tmp_path / "fensu.toml").write_text(
        "[targets.web]\n"
        f'analyzer = "{test_case.analyzer}"\n'
        'roots = ["missing"]\n'
        'rule_paths = ["rules/custom.py"]\n',
        encoding="utf-8",
    )
    custom_rule: Path = tmp_path / "rules/custom.py"
    custom_rule.parent.mkdir()
    custom_rule.write_text(
        f"from pathlib import Path\nPath({str(marker)!r}).touch()\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(
        check_setup_module,
        "discover_files",
        lambda **_kwargs: pytest.fail("discovery must not run for an unavailable backend"),
    )
    monkeypatch.chdir(tmp_path)
    stdout: CaptureOutput = CaptureOutput()
    stderr: CaptureOutput = CaptureOutput()

    exit_code: int = run_check(
        argv=("--no-color", "--no-cache", "--target", "web"),
        stdout=stdout,
        stderr=stderr,
    )

    assert exit_code == test_case.expected_exit_code
    assert stdout.getvalue() == ""
    assert test_case.expected_error_fragment in stderr.getvalue()
    assert not marker.exists()


@pytest.mark.parametrize(
    "test_case",
    [
        AggregateAnalyzerPreflightTestCase(
            description="later unavailable backend preempts earlier malformed Python target",
            expected_exit_code=2,
            expected_error_fragment="Known analyzer backend unavailable: svelte",
            expected_absent_fragment="Custom rule path does not exist",
        )
    ],
    ids=lambda case: case.description,
)
def test_given_mixed_aggregate_targets_when_running_python_host_then_all_backends_preflight_first(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    test_case: AggregateAnalyzerPreflightTestCase,
) -> None:
    (tmp_path / "fensu.toml").write_text(
        "[targets.alpha]\n"
        'analyzer = "python"\n'
        'roots = ["src/python"]\n'
        'rule_paths = ["rules/missing.py"]\n'
        "[targets.zeta]\n"
        'analyzer = "svelte"\n'
        'roots = ["src/web"]\n',
        encoding="utf-8",
    )
    monkeypatch.setattr(
        check_setup_module,
        "discover_files",
        lambda **_kwargs: pytest.fail("discovery must not run before aggregate preflight"),
    )
    monkeypatch.chdir(tmp_path)
    stdout: CaptureOutput = CaptureOutput()
    stderr: CaptureOutput = CaptureOutput()

    exit_code: int = run_check(
        argv=("--no-color", "--no-cache"),
        stdout=stdout,
        stderr=stderr,
    )

    assert exit_code == test_case.expected_exit_code
    assert test_case.expected_error_fragment in stderr.getvalue()
    assert test_case.expected_absent_fragment not in stderr.getvalue()


@pytest.mark.skipif(sys.platform == "win32", reason="symlink creation requires Windows privileges")
@pytest.mark.parametrize(
    "test_case",
    [
        CanonicalAliasCheckTestCase(
            description="Python diagnostics match Rust canonical alias behavior",
            expected_exit_code=1,
            expected_present="canonical/src/pkg/module.py",
            expected_alias_absent="alias/src/pkg/module.py",
            expected_double_prefix_absent="canonical/canonical/",
            expected_stderr="",
        )
    ],
    ids=lambda case: case.description,
)
def test_given_internal_target_alias_when_checking_then_reports_canonical_prefix_once(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    test_case: CanonicalAliasCheckTestCase,
) -> None:
    (tmp_path / "fensu.toml").write_text(
        "[targets.app]\n"
        'analyzer = "python"\n'
        'root = "alias"\n'
        'roots = ["src/pkg"]\n'
        "tests = []\n"
        "tooling = []\n"
        'select = ["FFA101"]\n',
        encoding="utf-8",
    )
    source: Path = tmp_path / "canonical/src/pkg/module.py"
    source.parent.mkdir(parents=True)
    source.write_text("VALUE = 1\n", encoding="utf-8")
    (tmp_path / "alias").symlink_to(tmp_path / "canonical", target_is_directory=True)
    monkeypatch.chdir(tmp_path)
    stdout: CaptureOutput = CaptureOutput()
    stderr: CaptureOutput = CaptureOutput()

    exit_code: int = run_check(
        argv=("--no-color", "--no-cache", "--target", "app"),
        stdout=stdout,
        stderr=stderr,
    )
    output: str = stdout.getvalue()

    assert exit_code == test_case.expected_exit_code
    assert test_case.expected_present in output
    assert test_case.expected_alias_absent not in output
    assert test_case.expected_double_prefix_absent not in output
    assert stderr.getvalue() == test_case.expected_stderr


@pytest.mark.parametrize(
    "test_case",
    [
        TargetCheckTestCase(
            description="selected custom-rule target evaluates repository-relative source",
            argv=("--no-color", "--no-cache", "--target", "custom"),
            expected_exit_code=1,
            expected_stdout_fragment=(
                "XNT001  named target fault\n --> frontend/scripts/tool.py:1:0"
            ),
            expected_stderr_fragment="",
        ),
        TargetCheckTestCase(
            description="multiple custom-host targets aggregate all local policies",
            argv=("--no-color", "--no-cache"),
            expected_exit_code=1,
            expected_stdout_fragment="Found 4 faults",
            expected_stderr_fragment="",
        ),
        TargetCheckTestCase(
            description="unknown custom-host target is rejected",
            argv=("--no-color", "--no-cache", "--target", "missing"),
            expected_exit_code=2,
            expected_stdout_fragment="",
            expected_stderr_fragment="Unknown target name: missing",
        ),
        TargetCheckTestCase(
            description="multiple custom-host targets reject positional paths",
            argv=("--no-color", "--no-cache", "src/core"),
            expected_exit_code=2,
            expected_stdout_fragment="",
            expected_stderr_fragment="Positional paths require exactly one selected target",
        ),
        TargetCheckTestCase(
            description="Python host reads target-local pyproject entrypoints",
            argv=("--no-color", "--no-cache", "--target", "metadata"),
            expected_exit_code=0,
            expected_stdout_fragment="Found 0 faults",
            expected_stderr_fragment="",
        ),
        TargetCheckTestCase(
            description="Python host applies target-local symbol exception without staleness",
            argv=("--no-color", "--no-cache", "--target", "symbol-exception"),
            expected_exit_code=1,
            expected_stdout_fragment="exceptions-symbol/src/pkg/external.py:5:",
            expected_stderr_fragment="",
        ),
        TargetCheckTestCase(
            description="Python host applies target-local file exception without staleness",
            argv=("--no-color", "--no-cache", "--target", "file-exception"),
            expected_exit_code=0,
            expected_stdout_fragment="Applied 1 rule exception",
            expected_stderr_fragment="",
        ),
    ],
    ids=lambda case: case.description,
)
def test_given_named_targets_when_running_custom_host_then_uses_same_selection_semantics(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    test_case: TargetCheckTestCase,
) -> None:
    (tmp_path / "fensu.toml").write_text(
        "[targets.core]\n"
        'analyzer = "python"\n'
        'roots = ["src/core"]\n'
        "tests = []\n"
        'select = ["FFA101"]\n'
        "[targets.custom]\n"
        'analyzer = "python"\n'
        'root = "frontend"\n'
        'roots = ["src/custom"]\n'
        'tests = ["tests"]\n'
        'tooling = ["scripts"]\n'
        'select = ["XNT001"]\n'
        'rule_paths = ["rules/named_target.py"]\n'
        "[targets.metadata]\n"
        'analyzer = "python"\n'
        'root = "metadata"\n'
        'roots = ["src/pkg"]\n'
        "tests = []\n"
        "tooling = []\n"
        'select = ["FFL105"]\n'
        "[targets.symbol-exception]\n"
        'analyzer = "python"\n'
        'root = "exceptions-symbol"\n'
        'roots = ["src/pkg"]\n'
        "tests = []\n"
        "tooling = []\n"
        'select = ["FFS120"]\n'
        "[targets.symbol-exception.thresholds]\n"
        "max_positional_args = 0\n"
        "[[targets.symbol-exception.rule_exceptions]]\n"
        'rule = "FFS120"\n'
        'path = "src/pkg/external.py"\n'
        'symbols = ["callback"]\n'
        'reason = "External callback remains positional."\n'
        "[targets.file-exception]\n"
        'analyzer = "python"\n'
        'root = "exceptions-file"\n'
        'roots = ["src/pkg"]\n'
        "tests = []\n"
        "tooling = []\n"
        'select = ["FFA001"]\n'
        "[[targets.file-exception.rule_exceptions]]\n"
        'rule = "FFA001"\n'
        'path = "src/pkg/external.py"\n'
        'reason = "Accepted file callback."\n',
        encoding="utf-8",
    )
    core: Path = tmp_path / "src/core/module.py"
    core.parent.mkdir(parents=True)
    core.write_text("CORE: int = 1\n", encoding="utf-8")
    custom: Path = tmp_path / "frontend/src/custom/module.py"
    custom.parent.mkdir(parents=True)
    custom.write_text("CUSTOM: int = 1\n", encoding="utf-8")
    target_test: Path = tmp_path / "frontend/tests/test_module.py"
    target_test.parent.mkdir(parents=True)
    target_test.write_text("TEST_VALUE: int = 1\n", encoding="utf-8")
    target_tool: Path = tmp_path / "frontend/scripts/tool.py"
    target_tool.parent.mkdir(parents=True)
    target_tool.write_text("TOOL_VALUE: int = 1\n", encoding="utf-8")
    rule: Path = tmp_path / "frontend/rules/named_target.py"
    rule.parent.mkdir()
    rule.write_text(
        "import ast\n"
        "from fensu import Family, Fault, RuleContext, rule\n"
        "@rule(code='XNT001', family=Family.CUSTOM, slug='named-target', "
        "message='named target fault')\n"
        "def named_target(module: ast.Module, ctx: RuleContext) -> list[Fault]:\n"
        "    return [ctx.fault(node=module.body[0])]\n",
        encoding="utf-8",
    )
    entry: Path = tmp_path / "metadata/src/pkg/orders/main/run.py"
    entry.parent.mkdir(parents=True)
    entry.write_text("def run() -> None:\n    pass\n", encoding="utf-8")
    (tmp_path / "metadata/pyproject.toml").write_text(
        "[project]\n"
        'name = "metadata"\n'
        'version = "0.0.0"\n'
        "[project.scripts]\n"
        'run = "pkg.orders.main.run:run"\n',
        encoding="utf-8",
    )
    symbol_exception: Path = tmp_path / "exceptions-symbol/src/pkg/external.py"
    symbol_exception.parent.mkdir(parents=True)
    symbol_exception.write_text(
        "def callback(value: int) -> None:\n"
        "    return None\n\n\n"
        "def retained(value: int) -> None:\n"
        "    return None\n",
        encoding="utf-8",
    )
    file_exception: Path = tmp_path / "exceptions-file/src/pkg/external.py"
    file_exception.parent.mkdir(parents=True)
    file_exception.write_text(
        "def callback(value):\n    return value\n",
        encoding="utf-8",
    )
    monkeypatch.chdir(tmp_path)
    stdout: CaptureOutput = CaptureOutput()
    stderr: CaptureOutput = CaptureOutput()

    exit_code: int = run_check(argv=test_case.argv, stdout=stdout, stderr=stderr)

    assert exit_code == test_case.expected_exit_code
    assert test_case.expected_stdout_fragment in stdout.getvalue()
    assert test_case.expected_stderr_fragment in stderr.getvalue()


@pytest.mark.parametrize(
    "test_case",
    [
        MultiTargetCacheCheckTestCase(
            description="all enabled targets retain isolated warm generations",
            beta_cache_enabled=True,
            argv=("--no-color", "--cache-stats"),
            expected_cold_stats="hits=0 misses=2",
            expected_warm_stats="hits=2 misses=0",
            expected_database_count=2,
        ),
        MultiTargetCacheCheckTestCase(
            description="mixed target defaults atomically disable aggregate caching",
            beta_cache_enabled=False,
            argv=("--no-color", "--cache-stats"),
            expected_cold_stats="",
            expected_warm_stats="",
            expected_database_count=0,
        ),
    ],
    ids=lambda case: case.description,
)
def test_given_multi_target_cache_policy_when_checking_twice_then_uses_atomic_isolated_generations(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    test_case: MultiTargetCacheCheckTestCase,
) -> None:
    write_cacheable_target_project(root=tmp_path, beta_cache_enabled=test_case.beta_cache_enabled)
    monkeypatch.chdir(tmp_path)
    cold_stdout: CaptureOutput = CaptureOutput()
    cold_stderr: CaptureOutput = CaptureOutput()
    warm_stdout: CaptureOutput = CaptureOutput()
    warm_stderr: CaptureOutput = CaptureOutput()

    cold_exit: int = run_check(
        argv=test_case.argv,
        stdout=cold_stdout,
        stderr=cold_stderr,
    )
    warm_exit: int = run_check(
        argv=test_case.argv,
        stdout=warm_stdout,
        stderr=warm_stderr,
    )
    databases: tuple[Path, ...] = tuple(tmp_path.glob(".fensu/cache/targets/*/.fensu/cache/v4.db"))

    assert cold_exit == 1
    assert warm_exit == 1
    assert cold_stdout.getvalue() == warm_stdout.getvalue()
    assert cold_stderr.getvalue().count("Cache:") == int(bool(test_case.expected_cold_stats))
    assert warm_stderr.getvalue().count("Cache:") == int(bool(test_case.expected_warm_stats))
    assert test_case.expected_cold_stats in cold_stderr.getvalue()
    assert test_case.expected_warm_stats in warm_stderr.getvalue()
    assert len(databases) == test_case.expected_database_count


@pytest.mark.parametrize(
    "test_case",
    [
        MultiTargetCacheCheckTestCase(
            description="CLI cache override enables every mixed-default target",
            beta_cache_enabled=False,
            argv=("--no-color", "--cache", "--cache-stats"),
            expected_cold_stats="hits=0 misses=2",
            expected_warm_stats="hits=2 misses=0",
            expected_database_count=2,
        )
    ],
    ids=lambda case: case.description,
)
def test_given_mixed_target_cache_defaults_when_forcing_cache_then_all_targets_become_warm(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    test_case: MultiTargetCacheCheckTestCase,
) -> None:
    write_cacheable_target_project(root=tmp_path, beta_cache_enabled=test_case.beta_cache_enabled)
    monkeypatch.chdir(tmp_path)
    cold_stderr: CaptureOutput = CaptureOutput()
    warm_stderr: CaptureOutput = CaptureOutput()

    cold_exit: int = run_check(argv=test_case.argv, stderr=cold_stderr)
    warm_exit: int = run_check(argv=test_case.argv, stderr=warm_stderr)
    databases: tuple[Path, ...] = tuple(tmp_path.glob(".fensu/cache/targets/*/.fensu/cache/v4.db"))

    assert cold_exit == 1
    assert warm_exit == 1
    assert test_case.expected_cold_stats in cold_stderr.getvalue()
    assert test_case.expected_warm_stats in warm_stderr.getvalue()
    assert len(databases) == test_case.expected_database_count


@pytest.mark.parametrize(
    "test_case",
    [
        TargetCheckTestCase(
            description="aggregate storage failure emits one degradation warning and status",
            argv=("--no-color", "--cache", "--cache-stats"),
            expected_exit_code=1,
            expected_stdout_fragment="Found 1 fault",
            expected_stderr_fragment="cache publication failed",
        )
    ],
    ids=lambda case: case.description,
)
def test_given_multi_target_cache_degradation_when_checking_then_reports_once(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    test_case: TargetCheckTestCase,
) -> None:
    write_cacheable_target_project(root=tmp_path, beta_cache_enabled=True)
    monkeypatch.chdir(tmp_path)
    stdout: CaptureOutput = CaptureOutput()
    stderr: CaptureOutput = CaptureOutput()

    def failed_publication(cache: ResultCache, **kwargs: object) -> CacheStats:
        del cache, kwargs
        return CacheStats(storage_failed=True)

    monkeypatch.setattr(ResultCache, "publish_native_generation", failed_publication)

    exit_code: int = run_check(argv=test_case.argv, stdout=stdout, stderr=stderr)

    assert exit_code == test_case.expected_exit_code
    assert test_case.expected_stdout_fragment in stdout.getvalue()
    assert stderr.getvalue().count(test_case.expected_stderr_fragment) == 1
    assert stderr.getvalue().count("Cache:") == 1


@pytest.mark.parametrize(
    "test_case",
    [
        MultiTargetCacheCheckTestCase(
            description="warm mixed-cacheability run retains hits and reports fresh work",
            beta_cache_enabled=True,
            argv=("--no-color", "--cache-stats"),
            expected_cold_stats="hits=0 misses=1 invalidations=0 writes=1 non_cacheable=1",
            expected_warm_stats="hits=1 misses=0 invalidations=0 writes=0 non_cacheable=1",
            expected_database_count=1,
        )
    ],
    ids=lambda case: case.description,
)
def test_given_cacheable_and_non_cacheable_targets_when_checking_warm_then_stats_are_conservative(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    test_case: MultiTargetCacheCheckTestCase,
) -> None:
    write_mixed_cacheability_target_project(root=tmp_path)
    monkeypatch.chdir(tmp_path)
    cold_stderr: CaptureOutput = CaptureOutput()
    warm_stderr: CaptureOutput = CaptureOutput()

    cold_exit: int = run_check(argv=test_case.argv, stderr=cold_stderr)
    warm_exit: int = run_check(argv=test_case.argv, stderr=warm_stderr)
    databases: tuple[Path, ...] = tuple(tmp_path.glob(".fensu/cache/targets/*/.fensu/cache/v4.db"))

    assert cold_exit == 1
    assert warm_exit == 1
    assert test_case.expected_cold_stats in cold_stderr.getvalue()
    assert test_case.expected_warm_stats in warm_stderr.getvalue()
    assert "non_cacheable=0" not in warm_stderr.getvalue()
    assert len(databases) == test_case.expected_database_count


@pytest.mark.parametrize(
    "test_case",
    [
        TargetCheckTestCase(
            description="identical advice is grouped and differing advice is target attributed",
            argv=("--no-color", "--cache-stats"),
            expected_exit_code=1,
            expected_stdout_fragment="Found 3 faults",
            expected_stderr_fragment="non_cacheable=3",
        )
    ],
    ids=lambda case: case.description,
)
def test_given_duplicate_and_distinct_cacheability_advice_when_checking_then_groups_deterministically(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    test_case: TargetCheckTestCase,
) -> None:
    write_cacheability_advice_target_project(root=tmp_path)
    monkeypatch.chdir(tmp_path)
    stdout: CaptureOutput = CaptureOutput()
    stderr: CaptureOutput = CaptureOutput()

    exit_code: int = run_check(argv=test_case.argv, stdout=stdout, stderr=stderr)
    advice: tuple[str, ...] = tuple(
        re.findall(r"^Custom rules appear.*$", stderr.getvalue(), flags=re.MULTILINE)
    )

    assert exit_code == test_case.expected_exit_code
    assert test_case.expected_stdout_fragment in stdout.getvalue()
    assert test_case.expected_stderr_fragment in stderr.getvalue()
    assert advice == (
        "Custom rules appear cacheable for targets alpha, beta; declare cacheable=True to enable "
        "caching for them: XAD001",
        "Custom rules appear cacheable for target gamma; declare cacheable=True to enable "
        "caching for them: XAD002",
    )


@pytest.mark.parametrize(
    "test_case",
    [
        MultiTargetThresholdOrderTestCase(
            description="threshold metadata uses every differing field for stable ordering",
            expected_first="max_arguments=1 path=src/pkg/module.py",
            expected_second="max_arguments=2 path=src/pkg/module.py",
            expected_exit_code=1,
        )
    ],
    ids=lambda case: case.description,
)
def test_given_threshold_uses_that_differ_by_value_and_reason_when_checking_in_processes_then_order_is_stable(
    tmp_path: Path,
    test_case: MultiTargetThresholdOrderTestCase,
) -> None:
    (tmp_path / "fensu.toml").write_text(
        "[targets.alpha]\n"
        'analyzer = "python"\n'
        'roots = ["src/pkg"]\n'
        "tests = []\n"
        "tooling = []\n"
        'select = ["FFS010"]\n'
        "[[targets.alpha.threshold_overrides]]\n"
        'paths = ["src/pkg/module.py"]\n'
        "thresholds = { max_arguments = 2 }\n"
        'reason = "alpha later value"\n'
        "[targets.zeta]\n"
        'analyzer = "python"\n'
        'roots = ["src/pkg"]\n'
        "tests = []\n"
        "tooling = []\n"
        'select = ["FFS010"]\n'
        "[[targets.zeta.threshold_overrides]]\n"
        'paths = ["src/pkg/module.py"]\n'
        "thresholds = { max_arguments = 1 }\n"
        'reason = "zeta earlier value"\n',
        encoding="utf-8",
    )
    source: Path = tmp_path / "src/pkg/module.py"
    source.parent.mkdir(parents=True)
    source.write_text(
        "def example(first: int, second: int, third: int) -> None:\n    return None\n",
        encoding="utf-8",
    )

    first: subprocess.CompletedProcess[str] = run_custom_check_process(
        root=tmp_path, argv=("--no-color", "--no-cache")
    )
    second: subprocess.CompletedProcess[str] = run_custom_check_process(
        root=tmp_path, argv=("--no-color", "--no-cache")
    )

    assert first.returncode == test_case.expected_exit_code
    assert second.returncode == test_case.expected_exit_code
    assert first.stdout == second.stdout
    assert first.stdout.index(test_case.expected_first) < first.stdout.index(
        test_case.expected_second
    )
