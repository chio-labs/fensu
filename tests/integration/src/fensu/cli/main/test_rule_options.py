"""Separate-process integration tests for typed custom-rule CLI options."""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from tests.integration.src.fensu.cli.main._test_types import (
    CustomRuleOptionProcessTestCase,
    InvalidCustomRuleOptionProcessTestCase,
)
from tests.integration.src.fensu.cli.main.helpers import (
    run_custom_check_process,
    write_custom_rule_option_project,
)


@pytest.mark.parametrize(
    "test_case",
    [
        CustomRuleOptionProcessTestCase(
            description="declared default and repository override change emitted diagnostics",
            override_value=2,
            expected_default_fault_count=1,
            expected_override_fault_count=2,
            expected_exit_code=1,
        )
    ],
    ids=lambda case: case.description,
)
def test_given_typed_custom_rule_option_when_checking_then_default_and_override_change_diagnostics(
    tmp_path: Path,
    test_case: CustomRuleOptionProcessTestCase,
) -> None:
    write_custom_rule_option_project(root=tmp_path)

    default: subprocess.CompletedProcess[str] = run_custom_check_process(
        root=tmp_path,
        argv=("--no-color", "--no-cache"),
    )
    config_path: Path = tmp_path / "fensu.toml"
    config_path.write_text(
        config_path.read_text(encoding="utf-8")
        + f"\n[rule_options.XOP001]\nlimit = {test_case.override_value}\n",
        encoding="utf-8",
    )
    overridden: subprocess.CompletedProcess[str] = run_custom_check_process(
        root=tmp_path,
        argv=("--no-color", "--no-cache"),
    )

    assert default.returncode == test_case.expected_exit_code
    assert overridden.returncode == test_case.expected_exit_code
    assert default.stdout.count("XOP001  ") == test_case.expected_default_fault_count
    assert overridden.stdout.count("XOP001  ") == test_case.expected_override_fault_count
    assert "configured finding limit=1" in default.stdout
    assert f"configured finding limit={test_case.override_value}" in overridden.stdout


@pytest.mark.parametrize(
    "test_case",
    [
        InvalidCustomRuleOptionProcessTestCase(
            description="invalid typed override is rejected before custom rule evaluation",
            option_table='\n[rule_options.XOP001]\nlimit = "two"\n',
            expected_exit_code=2,
            expected_error_fragment="Rule XOP001 option limit must be an integer",
            expected_evaluation_marker=False,
        )
    ],
    ids=lambda case: case.description,
)
def test_given_invalid_custom_rule_override_when_checking_then_validation_precedes_evaluation(
    tmp_path: Path,
    test_case: InvalidCustomRuleOptionProcessTestCase,
) -> None:
    write_custom_rule_option_project(
        root=tmp_path,
        option_table=test_case.option_table,
        evaluation_marker=True,
    )

    completed: subprocess.CompletedProcess[str] = run_custom_check_process(
        root=tmp_path,
        argv=("--no-color", "--no-cache"),
    )

    assert completed.returncode == test_case.expected_exit_code
    assert test_case.expected_error_fragment in completed.stderr
    assert (tmp_path / "evaluation-ran").exists() is test_case.expected_evaluation_marker
    assert completed.stdout == ""
