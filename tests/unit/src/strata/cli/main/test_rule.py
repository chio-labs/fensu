"""Tests for `strata rule` metadata inspection."""

from __future__ import annotations

from pathlib import Path

import pytest

from strata.cli.main.rule import run_rule
from tests.unit.src.strata.cli.main._test_types import MetadataCommandTestCase
from tests.unit.src.strata.cli.main.helpers import CaptureOutput, write_cli_fixture_project


@pytest.mark.parametrize(
    "test_case",
    [
        MetadataCommandTestCase(
            description="configured custom rule renders complete metadata",
            argv=("XCK001",),
            expected_exit_code=0,
            expected_output_fragments=(
                "XCK001 always",
                "Family: custom",
                "Kind: custom",
                "Message: custom fault",
                "Remediation: apply the custom remediation",
                "Source:",
            ),
        ),
        MetadataCommandTestCase(
            description="ignored core rule remains inspectable",
            argv=("SFS131",),
            expected_exit_code=0,
            expected_output_fragments=(
                "SFS131 no-complex-comprehensions",
                "Family: shape",
                "Kind: core",
                "Source: core",
            ),
        ),
    ],
    ids=lambda case: case.description,
)
def test_given_known_custom_rule_when_inspecting_then_renders_single_sourced_metadata(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    test_case: MetadataCommandTestCase,
) -> None:
    write_cli_fixture_project(root=tmp_path, rule_code="XCK001")
    monkeypatch.chdir(tmp_path)
    stdout: CaptureOutput = CaptureOutput()
    stderr: CaptureOutput = CaptureOutput()

    exit_code: int = run_rule(argv=test_case.argv, stdout=stdout, stderr=stderr)

    assert exit_code == test_case.expected_exit_code
    assert all(fragment in stdout.getvalue() for fragment in test_case.expected_output_fragments)


@pytest.mark.parametrize(
    "test_case",
    [
        MetadataCommandTestCase(
            description="unknown rule returns clear command error",
            argv=("UNKNOWN",),
            expected_exit_code=2,
            expected_output_fragments=("Unknown rule code: UNKNOWN",),
        )
    ],
    ids=lambda case: case.description,
)
def test_given_unknown_rule_when_inspecting_then_returns_clear_error(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    test_case: MetadataCommandTestCase,
) -> None:
    write_cli_fixture_project(root=tmp_path, rule_code="XCK001")
    monkeypatch.chdir(tmp_path)
    stdout: CaptureOutput = CaptureOutput()
    stderr: CaptureOutput = CaptureOutput()

    exit_code: int = run_rule(argv=test_case.argv, stdout=stdout, stderr=stderr)

    assert exit_code == test_case.expected_exit_code
    assert all(fragment in stderr.getvalue() for fragment in test_case.expected_output_fragments)
