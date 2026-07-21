"""Integration tests for source-owned custom-rule coverage evaluation."""

from __future__ import annotations

from pathlib import Path

import pytest

from fensu.cli.main.custom_check_host import run_custom_check as run_check
from tests.integration.src.fensu.cli.main._test_types import (
    CheckErrorTestCase,
    CustomRuleCoverageCacheTestCase,
    CustomRuleCoverageTestCase,
    CustomRuleCoverageWarningTestCase,
)
from tests.integration.src.fensu.cli.main.helpers import (
    CaptureOutput,
    write_custom_rule_coverage_project,
)

_DIRECT_CASE: str = (
    "from fensu import RuleCase, evaluate_rule\n"
    "from rules.custom_rule import first_rule\n\n"
    "def test_given_source_when_checking_then_matches() -> None:\n"
    "    result = evaluate_rule(rule=first_rule, test_case=RuleCase(description='one', "
    "source='VALUE: int = 1', expected_fault_count=0))\n"
)
_ALIASED_CASES: str = (
    "import rules.custom_rule as policy\n"
    "import fensu as st\n\n"
    "@pytest.mark.parametrize('backend', ['a', 'b', 'c'])\n"
    "@pytest.mark.parametrize('test_case', [\n"
    "    st.RuleCase(description='pass', source='VALUE: int = 1', expected_fault_count=0),\n"
    "    st.RuleCase(description='fail', source='VALUE = 1', expected_fault_count=1),\n"
    "])\n"
    "def test_given_source_when_checking_then_matches(test_case, backend) -> None:\n"
    "    result = st.evaluate_rule(rule=policy.first_rule, test_case=test_case)\n"
)
_DYNAMIC_CASES: str = (
    "from fensu import evaluate_rule\n"
    "from rules.custom_rule import first_rule\n\n"
    "@pytest.mark.parametrize('test_case', load_cases())\n"
    "def test_given_source_when_checking_then_matches(test_case) -> None:\n"
    "    result = evaluate_rule(rule=first_rule, test_case=test_case)\n"
)


@pytest.mark.parametrize(
    "test_case",
    [
        CustomRuleCoverageTestCase(
            description="rule path without tests reports one declaration-owned fault",
            test_source=None,
            minimum=1,
            use_rule_module=False,
            second_rule=False,
            expected_fault_count=1,
            expected_output_fragment="custom rule XCV001 has 0 statically declared test cases",
        ),
        CustomRuleCoverageTestCase(
            description="direct literal RuleCase satisfies the default boundary",
            test_source=_DIRECT_CASE,
            minimum=1,
            use_rule_module=False,
            second_rule=False,
            expected_fault_count=0,
            expected_output_fragment="Found 0 faults",
        ),
        CustomRuleCoverageTestCase(
            description="aliased module-qualified stacked cases count only policy dimension",
            test_source=_ALIASED_CASES,
            minimum=2,
            use_rule_module=False,
            second_rule=False,
            expected_fault_count=0,
            expected_output_fragment="Found 0 faults",
        ),
        CustomRuleCoverageTestCase(
            description="dynamic cases remain associated but cannot prove cardinality",
            test_source=_DYNAMIC_CASES,
            minimum=1,
            use_rule_module=False,
            second_rule=False,
            expected_fault_count=1,
            expected_output_fragment="associated tests with dynamically determined case counts",
        ),
        CustomRuleCoverageTestCase(
            description="unselected second rule from one source receives its own diagnostic",
            test_source=_DIRECT_CASE,
            minimum=1,
            use_rule_module=False,
            second_rule=True,
            expected_fault_count=1,
            expected_output_fragment="custom rule XCV002 has 0 statically declared test cases",
        ),
        CustomRuleCoverageTestCase(
            description="repository-owned rule module participates in coverage",
            test_source=_DIRECT_CASE,
            minimum=1,
            use_rule_module=True,
            second_rule=False,
            expected_fault_count=0,
            expected_output_fragment="Found 0 faults",
        ),
        CustomRuleCoverageTestCase(
            description="zero threshold disables coverage diagnostics",
            test_source=None,
            minimum=0,
            use_rule_module=False,
            second_rule=True,
            expected_fault_count=0,
            expected_output_fragment="Found 0 faults",
        ),
    ],
    ids=lambda case: case.description,
)
def test_given_configured_custom_rules_when_checking_coverage_then_reports_source_owned_results(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    test_case: CustomRuleCoverageTestCase,
) -> None:
    write_custom_rule_coverage_project(
        root=tmp_path,
        test_source=test_case.test_source,
        minimum=test_case.minimum,
        use_rule_module=test_case.use_rule_module,
        second_rule=test_case.second_rule,
    )
    monkeypatch.chdir(tmp_path)
    stdout: CaptureOutput = CaptureOutput()

    exit_code: int = run_check(argv=("--no-color", "--no-cache"), stdout=stdout)

    assert exit_code == {0: 0, 1: 1}[test_case.expected_fault_count]
    assert stdout.getvalue().count("FFR707  ") == test_case.expected_fault_count
    assert test_case.expected_output_fragment in stdout.getvalue()
    assert "rules/custom_rule.py:" in stdout.getvalue() or test_case.expected_fault_count == 0


@pytest.mark.parametrize(
    "test_case",
    [
        CustomRuleCoverageCacheTestCase(
            description="test add rename and remove invalidate the source-owned cache record",
            expected_cold_stats="hits=0 misses=2",
            expected_warm_stats="hits=2 misses=0",
            expected_add_stats="hits=1 misses=1 invalidations=1",
            expected_remove_stats="hits=1 misses=0 invalidations=2",
            expected_fault_fragment="custom rule XCV001 has 0 statically declared test cases",
        )
    ],
    ids=lambda case: case.description,
)
def test_given_cached_coverage_when_test_namespace_changes_then_invalidates_rule_source_owner(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    test_case: CustomRuleCoverageCacheTestCase,
) -> None:
    write_custom_rule_coverage_project(
        root=tmp_path,
        test_source=None,
        minimum=1,
        use_rule_module=False,
        second_rule=False,
    )
    (tmp_path / "fensu.toml").write_text(
        (tmp_path / "fensu.toml").read_text(encoding="utf-8") + "\n[cache]\nenabled = true\n",
        encoding="utf-8",
    )
    monkeypatch.chdir(tmp_path)
    argv: tuple[str, ...] = ("--no-color", "--cache", "--cache-stats")
    cold_stdout: CaptureOutput = CaptureOutput()
    cold_stderr: CaptureOutput = CaptureOutput()
    warm_stdout: CaptureOutput = CaptureOutput()
    warm_stderr: CaptureOutput = CaptureOutput()

    _ = run_check(argv=argv, stdout=cold_stdout, stderr=cold_stderr)
    _ = run_check(argv=argv, stdout=warm_stdout, stderr=warm_stderr)
    tests: Path = tmp_path / "tests"
    tests.mkdir()
    test_path: Path = tests / "test_custom_rule.py"
    test_path.write_text(_DIRECT_CASE, encoding="utf-8")
    add_stdout: CaptureOutput = CaptureOutput()
    add_stderr: CaptureOutput = CaptureOutput()
    _ = run_check(argv=argv, stdout=add_stdout, stderr=add_stderr)
    renamed_path: Path = test_path.with_name("test_policy.py")
    test_path.rename(renamed_path)
    rename_stdout: CaptureOutput = CaptureOutput()
    _ = run_check(argv=argv, stdout=rename_stdout, stderr=CaptureOutput())
    renamed_path.write_text(_DYNAMIC_CASES, encoding="utf-8")
    harness_stdout: CaptureOutput = CaptureOutput()
    harness_stderr: CaptureOutput = CaptureOutput()
    _ = run_check(argv=argv, stdout=harness_stdout, stderr=harness_stderr)
    renamed_path.write_text(_DIRECT_CASE, encoding="utf-8")
    _ = run_check(argv=argv, stdout=CaptureOutput(), stderr=CaptureOutput())
    config_path: Path = tmp_path / "fensu.toml"
    original_config: str = config_path.read_text(encoding="utf-8")
    config_path.write_text(
        original_config.replace("min_custom_rule_test_cases = 1", "min_custom_rule_test_cases = 2"),
        encoding="utf-8",
    )
    config_stdout: CaptureOutput = CaptureOutput()
    config_stderr: CaptureOutput = CaptureOutput()
    _ = run_check(argv=argv, stdout=config_stdout, stderr=config_stderr)
    config_path.write_text(original_config, encoding="utf-8")
    _ = run_check(argv=argv, stdout=CaptureOutput(), stderr=CaptureOutput())
    rule_path: Path = tmp_path / "rules/custom_rule.py"
    rule_path.write_text(rule_path.read_text(encoding="utf-8") + "\n", encoding="utf-8")
    rule_stdout: CaptureOutput = CaptureOutput()
    rule_stderr: CaptureOutput = CaptureOutput()
    _ = run_check(argv=argv, stdout=rule_stdout, stderr=rule_stderr)
    renamed_path.unlink()
    remove_stdout: CaptureOutput = CaptureOutput()
    remove_stderr: CaptureOutput = CaptureOutput()
    _ = run_check(argv=argv, stdout=remove_stdout, stderr=remove_stderr)
    config_path.write_text(
        config_path.read_text(encoding="utf-8").replace(
            'rule_paths = ["rules/custom_rule.py"]\n', ""
        ),
        encoding="utf-8",
    )
    cleanup_stdout: CaptureOutput = CaptureOutput()
    cleanup_stderr: CaptureOutput = CaptureOutput()
    _ = run_check(argv=argv, stdout=cleanup_stdout, stderr=cleanup_stderr)
    cleanup_warm_stderr: CaptureOutput = CaptureOutput()
    _ = run_check(argv=argv, stdout=CaptureOutput(), stderr=cleanup_warm_stderr)

    assert cold_stdout.getvalue() == warm_stdout.getvalue()
    assert test_case.expected_cold_stats in cold_stderr.getvalue()
    assert test_case.expected_warm_stats in warm_stderr.getvalue()
    assert test_case.expected_add_stats in add_stderr.getvalue()
    assert add_stdout.getvalue() == rename_stdout.getvalue()
    assert "dynamically determined case counts" in harness_stdout.getvalue()
    assert "invalidations=2" in harness_stderr.getvalue()
    assert "hits=0 misses=3" in config_stderr.getvalue()
    assert (
        "has 1 statically declared test cases; at least 2 is required" in config_stdout.getvalue()
    )
    assert "hits=0 misses=3" in rule_stderr.getvalue()
    assert "Found 0 faults" in rule_stdout.getvalue()
    assert test_case.expected_remove_stats in remove_stderr.getvalue()
    assert test_case.expected_fault_fragment in remove_stdout.getvalue()
    assert "hits=0 misses=1" in cleanup_stderr.getvalue()
    assert "hits=1 misses=0" in cleanup_warm_stderr.getvalue()
    assert "FFR707" not in cleanup_stdout.getvalue()


@pytest.mark.parametrize(
    "test_case",
    [
        CheckErrorTestCase(
            description="external rule module is rejected with source ownership remediation",
            argv=("--no-color", "--no-cache"),
            expected_exit_code=2,
            expected_error_fragment=("resolves outside the repository at "),
        )
    ],
    ids=lambda case: case.description,
)
def test_given_external_custom_rule_module_when_checking_then_returns_actionable_config_error(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    test_case: CheckErrorTestCase,
) -> None:
    module_name: str = f"external_policy_{tmp_path.name.replace('-', '_')}"
    external_path: Path = tmp_path.parent / f"{module_name}.py"
    external_path.write_text(
        "from __future__ import annotations\n\n"
        "import ast\n\n"
        "from fensu import Family, Fault, RuleContext, rule\n\n"
        "@rule(code='XEXT001', family=Family.CUSTOM, slug='external', message='external')\n"
        "def external_rule(module: ast.Module, ctx: RuleContext) -> list[Fault]:\n"
        "    del module, ctx\n"
        "    return []\n",
        encoding="utf-8",
    )
    (tmp_path / "src/pkg").mkdir(parents=True)
    (tmp_path / "src/pkg/target.py").write_text("VALUE: int = 1\n", encoding="utf-8")
    (tmp_path / "fensu.toml").write_text(
        f'roots = ["src/pkg"]\nselect = ["FFR707"]\nrule_modules = ["{module_name}"]\n',
        encoding="utf-8",
    )
    monkeypatch.syspath_prepend(tmp_path.parent)
    monkeypatch.chdir(tmp_path)
    stderr: CaptureOutput = CaptureOutput()

    exit_code: int = run_check(argv=test_case.argv, stdout=CaptureOutput(), stderr=stderr)

    assert exit_code == test_case.expected_exit_code
    assert test_case.expected_error_fragment in stderr.getvalue()
    assert "Move the rule into this repository" in stderr.getvalue()
    assert "FFR707 diagnostics and cache entries" in stderr.getvalue()


@pytest.mark.parametrize(
    "test_case",
    [
        CustomRuleCoverageWarningTestCase(
            description="warn-only coverage is skipped plainly and reported nonblocking with warn",
            expected_plain_summary="Found 0 faults",
            expected_warning_summary="Found 0 faults and 1 warning",
            expected_warning_fragment="custom rule XCV001 has 0 statically declared test cases",
            expected_plain_cold_stats="hits=0 misses=1",
            expected_plain_warm_stats="hits=1 misses=0",
            expected_warning_cold_stats="hits=0 misses=2",
            expected_warning_warm_stats="hits=2 misses=0",
        )
    ],
    ids=lambda case: case.description,
)
def test_given_warn_only_coverage_when_running_uncached_then_respects_warning_mode_and_tier(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    test_case: CustomRuleCoverageWarningTestCase,
) -> None:
    write_custom_rule_coverage_project(
        root=tmp_path,
        test_source=None,
        minimum=1,
        use_rule_module=False,
        second_rule=False,
        warn_only=True,
    )
    monkeypatch.chdir(tmp_path)
    plain_stdout: CaptureOutput = CaptureOutput()
    warning_stdout: CaptureOutput = CaptureOutput()

    plain_exit: int = run_check(
        argv=("--no-color", "--no-cache"), stdout=plain_stdout, stderr=CaptureOutput()
    )
    warning_exit: int = run_check(
        argv=("--no-color", "--no-cache", "--warn"),
        stdout=warning_stdout,
        stderr=CaptureOutput(),
    )

    assert plain_exit == 0
    assert warning_exit == 0
    assert test_case.expected_plain_summary in plain_stdout.getvalue()
    assert "FFR707" not in plain_stdout.getvalue()
    assert test_case.expected_warning_summary in warning_stdout.getvalue()
    assert test_case.expected_warning_fragment in warning_stdout.getvalue()
    assert warning_stdout.getvalue().count("FFR707  ") == 1
    assert "= warning:" in warning_stdout.getvalue()


@pytest.mark.parametrize(
    "test_case",
    [
        CustomRuleCoverageWarningTestCase(
            description="warn-only coverage has separate source-owned cold and warm cache records",
            expected_plain_summary="Found 0 faults",
            expected_warning_summary="Found 0 faults and 1 warning",
            expected_warning_fragment="custom rule XCV001 has 0 statically declared test cases",
            expected_plain_cold_stats="hits=0 misses=1",
            expected_plain_warm_stats="hits=1 misses=0",
            expected_warning_cold_stats="hits=0 misses=2",
            expected_warning_warm_stats="hits=2 misses=0",
        )
    ],
    ids=lambda case: case.description,
)
def test_given_warn_only_coverage_when_running_cached_then_replays_warning_source_record(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    test_case: CustomRuleCoverageWarningTestCase,
) -> None:
    write_custom_rule_coverage_project(
        root=tmp_path,
        test_source=None,
        minimum=1,
        use_rule_module=False,
        second_rule=False,
        warn_only=True,
    )
    monkeypatch.chdir(tmp_path)
    plain_argv: tuple[str, ...] = ("--no-color", "--cache", "--cache-stats")
    warning_argv: tuple[str, ...] = (*plain_argv, "--warn")
    plain_cold_stdout: CaptureOutput = CaptureOutput()
    plain_cold_stderr: CaptureOutput = CaptureOutput()
    plain_warm_stderr: CaptureOutput = CaptureOutput()
    warning_cold_stdout: CaptureOutput = CaptureOutput()
    warning_cold_stderr: CaptureOutput = CaptureOutput()
    warning_warm_stdout: CaptureOutput = CaptureOutput()
    warning_warm_stderr: CaptureOutput = CaptureOutput()

    plain_cold_exit: int = run_check(
        argv=plain_argv, stdout=plain_cold_stdout, stderr=plain_cold_stderr
    )
    plain_warm_exit: int = run_check(
        argv=plain_argv, stdout=CaptureOutput(), stderr=plain_warm_stderr
    )
    warning_cold_exit: int = run_check(
        argv=warning_argv, stdout=warning_cold_stdout, stderr=warning_cold_stderr
    )
    warning_warm_exit: int = run_check(
        argv=warning_argv, stdout=warning_warm_stdout, stderr=warning_warm_stderr
    )

    assert plain_cold_exit == 0
    assert plain_warm_exit == 0
    assert warning_cold_exit == 0
    assert warning_warm_exit == 0
    assert test_case.expected_plain_summary in plain_cold_stdout.getvalue()
    assert "FFR707" not in plain_cold_stdout.getvalue()
    assert test_case.expected_plain_cold_stats in plain_cold_stderr.getvalue()
    assert test_case.expected_plain_warm_stats in plain_warm_stderr.getvalue()
    assert warning_warm_stdout.getvalue() == warning_cold_stdout.getvalue()
    assert test_case.expected_warning_summary in warning_cold_stdout.getvalue()
    assert test_case.expected_warning_fragment in warning_cold_stdout.getvalue()
    assert warning_cold_stdout.getvalue().count("FFR707  ") == 1
    assert test_case.expected_warning_cold_stats in warning_cold_stderr.getvalue()
    assert test_case.expected_warning_warm_stats in warning_warm_stderr.getvalue()
