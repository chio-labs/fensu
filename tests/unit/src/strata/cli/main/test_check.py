"""Tests for `strata check` orchestration."""

from __future__ import annotations

from pathlib import Path

import pytest

from strata.cli.main.check import run_check
from tests.unit.src.strata.cli.main._test_types import CheckCommandTestCase, CheckNoFaultTestCase
from tests.unit.src.strata.cli.main.helpers import (
    CaptureOutput,
    write_cli_fixture_project,
    write_cli_no_fault_project,
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
