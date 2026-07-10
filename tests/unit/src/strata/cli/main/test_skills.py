"""Tests for repository-aware skill installation."""

from __future__ import annotations

from pathlib import Path

import pytest

from strata.agentdocs.core.constants import GENERATED_MARKER
from strata.cli.main.skills import run_skills
from strata.config.core.main.load_config import load_config
from strata.config.core.models import Config
from strata.rules.authoring.models import RuleSpec
from strata.rules.catalog.main.build_ruleset import build_ruleset
from tests.unit.src.strata.cli.main._test_types import SkillCommandTestCase
from tests.unit.src.strata.cli.main.helpers import CaptureOutput, write_cli_fixture_project


@pytest.mark.parametrize(
    "test_case",
    [
        SkillCommandTestCase(
            description="default update writes every repository-local target",
            argv=("update",),
            expected_exit_code=0,
            expected_output_fragments=("Updated Strata skill files:",),
            expected_written_paths=(
                ".opencode/skills/strata/SKILL.md",
                ".claude/skills/strata/SKILL.md",
                ".agents/skills/strata/SKILL.md",
            ),
            expected_absent_fragments=("## SFX002:",),
        ),
        SkillCommandTestCase(
            description="global target filter writes selected home locations",
            argv=("update", "--global", "--target", "opencode", "--target", "agents"),
            expected_exit_code=0,
            expected_output_fragments=("Updated Strata skill files:",),
            expected_written_paths=(
                "home/.config/opencode/skills/strata/SKILL.md",
                "home/.agents/skills/strata/SKILL.md",
            ),
            expected_absent_fragments=("## SFX002:",),
        ),
    ],
    ids=lambda case: case.description,
)
def test_given_scope_and_targets_when_updating_skills_then_installs_active_rule_guidance(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    test_case: SkillCommandTestCase,
) -> None:
    write_cli_fixture_project(root=tmp_path, rule_code="XCK001", include_core_rules=True)
    monkeypatch.chdir(tmp_path)
    stdout: CaptureOutput = CaptureOutput()
    stderr: CaptureOutput = CaptureOutput()
    config: Config = load_config(tmp_path)
    active_rules: tuple[RuleSpec, ...] = build_ruleset(config)
    active_rule_headings: tuple[str, ...] = tuple(
        f"## {rule.code}: {rule.slug}" for rule in active_rules
    )

    exit_code: int = run_skills(
        argv=test_case.argv,
        stdout=stdout,
        stderr=stderr,
        home_dir=tmp_path / "home",
    )

    assert exit_code == test_case.expected_exit_code
    assert all(fragment in stdout.getvalue() for fragment in test_case.expected_output_fragments)
    assert stderr.getvalue() == ""
    for relative_path in test_case.expected_written_paths:
        content: str = (tmp_path / relative_path).read_text(encoding="utf-8")
        assert GENERATED_MARKER in content
        assert "## Commands" in content
        assert "## Default Repository Shape" in content
        assert "## SFX001:" in content
        assert "## XCK001: always" in content
        assert "custom fault" in content
        assert all(heading in content for heading in active_rule_headings)
        assert all(fragment not in content for fragment in test_case.expected_absent_fragments)


@pytest.mark.parametrize(
    "test_case",
    [
        SkillCommandTestCase(
            description="non-generated file is preserved without force",
            argv=("update", "--target", "agents"),
            expected_exit_code=2,
            expected_output_fragments=("refusing to overwrite non-generated skill file",),
            expected_written_paths=(".agents/skills/strata/SKILL.md",),
            expected_file_fragment="user-authored guidance",
        ),
        SkillCommandTestCase(
            description="force replaces a non-generated file",
            argv=("update", "--target", "agents", "--force"),
            expected_exit_code=0,
            expected_output_fragments=("Updated Strata skill files:",),
            expected_written_paths=(".agents/skills/strata/SKILL.md",),
        ),
    ],
    ids=lambda case: case.description,
)
def test_given_existing_user_skill_when_updating_then_requires_explicit_force(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    test_case: SkillCommandTestCase,
) -> None:
    write_cli_fixture_project(root=tmp_path, rule_code="XCK001", include_core_rules=True)
    skill_path: Path = tmp_path / test_case.expected_written_paths[0]
    skill_path.parent.mkdir(parents=True)
    skill_path.write_text("user-authored guidance\n", encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    stdout: CaptureOutput = CaptureOutput()
    stderr: CaptureOutput = CaptureOutput()

    exit_code: int = run_skills(argv=test_case.argv, stdout=stdout, stderr=stderr)

    assert exit_code == test_case.expected_exit_code
    combined_output: str = f"{stdout.getvalue()}{stderr.getvalue()}"
    assert all(fragment in combined_output for fragment in test_case.expected_output_fragments)
    content: str = skill_path.read_text(encoding="utf-8")
    assert test_case.expected_file_fragment in content
