"""Installed CLI end-to-end tests for typed custom-rule options."""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from tests.e2e.src.fensu.cli.main._test_types import (
    CustomRuleOptionCacheCliTestCase,
    CustomRuleOptionJobsCliTestCase,
)
from tests.e2e.src.fensu.cli.main.helpers import (
    run_cli_check,
    write_custom_rule_option_project,
)


@pytest.mark.parametrize(
    "test_case",
    [
        CustomRuleOptionJobsCliTestCase(
            description="existing project dependency stays deterministic across jobs flag values",
            expected_exit_code=1,
            expected_fault_count=2,
            expected_output_fragment="configured finding limit=1",
        )
    ],
    ids=lambda case: case.description,
)
def test_given_existing_option_path_when_checking_with_jobs_then_output_is_deterministic(
    tmp_path: Path,
    test_case: CustomRuleOptionJobsCliTestCase,
) -> None:
    write_custom_rule_option_project(root=tmp_path)

    serial: subprocess.CompletedProcess[str] = run_cli_check(
        root=tmp_path,
        argv=("--no-cache", "--jobs", "1"),
    )
    jobs_two: subprocess.CompletedProcess[str] = run_cli_check(
        root=tmp_path,
        argv=("--no-cache", "--jobs", "2"),
    )

    assert serial.returncode == test_case.expected_exit_code
    assert jobs_two.returncode == test_case.expected_exit_code
    assert jobs_two.stdout == serial.stdout
    assert jobs_two.stderr == serial.stderr
    assert serial.stdout.count("XOP001  ") == test_case.expected_fault_count
    assert test_case.expected_output_fragment in jobs_two.stdout


@pytest.mark.parametrize(
    "test_case",
    [
        CustomRuleOptionCacheCliTestCase(
            description="same typed options hit cache while changed override misses",
            override_value=2,
            expected_exit_code=1,
            expected_default_fault_count=2,
            expected_override_fault_count=4,
            expected_cold_stats="hits=0 misses=2",
            expected_warm_stats="hits=2 misses=0",
            expected_override_stats="hits=0 misses=2",
        )
    ],
    ids=lambda case: case.description,
)
def test_given_cached_custom_rule_options_when_override_changes_then_cache_identity_changes(
    tmp_path: Path,
    test_case: CustomRuleOptionCacheCliTestCase,
) -> None:
    write_custom_rule_option_project(root=tmp_path)
    argv: tuple[str, ...] = ("--cache", "--cache-stats")

    cold: subprocess.CompletedProcess[str] = run_cli_check(root=tmp_path, argv=argv)
    warm: subprocess.CompletedProcess[str] = run_cli_check(root=tmp_path, argv=argv)
    config_path: Path = tmp_path / "fensu.toml"
    config_path.write_text(
        config_path.read_text(encoding="utf-8")
        + f"\n[rule_options.XOP001]\nlimit = {test_case.override_value}\n",
        encoding="utf-8",
    )
    overridden: subprocess.CompletedProcess[str] = run_cli_check(root=tmp_path, argv=argv)

    assert cold.returncode == test_case.expected_exit_code
    assert warm.returncode == test_case.expected_exit_code
    assert overridden.returncode == test_case.expected_exit_code
    assert cold.stdout.count("XOP001  ") == test_case.expected_default_fault_count
    assert warm.stdout == cold.stdout
    assert overridden.stdout.count("XOP001  ") == test_case.expected_override_fault_count
    assert test_case.expected_cold_stats in cold.stderr
    assert test_case.expected_warm_stats in warm.stderr
    assert test_case.expected_override_stats in overridden.stderr
