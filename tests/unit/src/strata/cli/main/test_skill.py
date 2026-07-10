"""Tests for `strata skill` agent-guidance generation."""

from __future__ import annotations

from pathlib import Path

import pytest

from strata.cli.main.skill import run_skill
from tests.unit.src.strata.cli.main._test_types import SkillCommandTestCase
from tests.unit.src.strata.cli.main.helpers import CaptureOutput, write_cli_fixture_project


@pytest.mark.parametrize(
    "test_case",
    [
        SkillCommandTestCase(
            description="active custom rule generates guidance on stdout",
            argv=(),
            expected_exit_code=0,
            expected_output_fragments=(
                "# Strata Architecture Rules",
                "## XCK001: always",
                "custom fault",
                "Remediation: apply the custom remediation",
            ),
        )
    ],
    ids=lambda case: case.description,
)
def test_given_active_rules_when_generating_skill_then_uses_rule_metadata(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    test_case: SkillCommandTestCase,
) -> None:
    write_cli_fixture_project(root=tmp_path, rule_code="XCK001")
    monkeypatch.chdir(tmp_path)
    stdout: CaptureOutput = CaptureOutput()
    stderr: CaptureOutput = CaptureOutput()

    exit_code: int = run_skill(argv=test_case.argv, stdout=stdout, stderr=stderr)

    assert exit_code == test_case.expected_exit_code
    assert all(fragment in stdout.getvalue() for fragment in test_case.expected_output_fragments)


@pytest.mark.parametrize(
    "test_case",
    [
        SkillCommandTestCase(
            description="output option writes generated guidance",
            argv=("--output", "generated/SKILL.md"),
            expected_exit_code=0,
            expected_output_fragments=("## XCK001: always",),
        )
    ],
    ids=lambda case: case.description,
)
def test_given_output_path_when_generating_skill_then_writes_document(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    test_case: SkillCommandTestCase,
) -> None:
    write_cli_fixture_project(root=tmp_path, rule_code="XCK001")
    monkeypatch.chdir(tmp_path)
    stdout: CaptureOutput = CaptureOutput()
    stderr: CaptureOutput = CaptureOutput()

    exit_code: int = run_skill(argv=test_case.argv, stdout=stdout, stderr=stderr)
    output: str = (tmp_path / "generated/SKILL.md").read_text(encoding="utf-8")

    assert exit_code == test_case.expected_exit_code
    assert all(fragment in output for fragment in test_case.expected_output_fragments)
