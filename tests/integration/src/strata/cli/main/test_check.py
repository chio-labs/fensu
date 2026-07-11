"""Tests for `strata check` orchestration."""

from __future__ import annotations

from pathlib import Path

import pytest

from strata.cli.main.check import run_check
from tests.integration.src.strata.cli.main._test_types import (
    CheckCommandTestCase,
    CheckErrorTestCase,
    CheckNoFaultTestCase,
)
from tests.integration.src.strata.cli.main.helpers import (
    CaptureOutput,
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
