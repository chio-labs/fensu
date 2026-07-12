"""Tests for repository-aware skill installation."""

from __future__ import annotations

from pathlib import Path

import pytest

from strata.agentdocs.constants import GENERATED_MARKER
from strata.agentdocs.helpers import installation
from strata.cli.main.skills import run_skills
from strata.config.main.load_config import load_config
from strata.config.models import Config
from strata.rules.authoring.models import RuleSpec
from strata.rules.catalog.main.build_ruleset import build_ruleset
from tests.integration.src.strata.cli.main._test_types import (
    SkillCommandTestCase,
    SkillTransactionFailureTestCase,
)
from tests.integration.src.strata.cli.main.helpers import (
    CaptureOutput,
    FailingSkillPublisher,
    RacingExistingSkillWriter,
    RacingSkillLinker,
    write_cli_fixture_project,
)


@pytest.mark.parametrize(
    "test_case",
    [
        SkillCommandTestCase(
            description="missing subcommand explains the valid update command",
            argv=(),
            expected_exit_code=2,
            expected_output_fragments=(
                "A skills command is required.",
                "`strata skills update`",
                "usage: strata skills",
            ),
        ),
        SkillCommandTestCase(
            description="update option typo explains that update is a subcommand",
            argv=("--update",),
            expected_exit_code=2,
            expected_output_fragments=(
                "`update` is a subcommand, not an option.",
                "`strata skills update`",
            ),
        ),
    ],
    ids=lambda case: case.description,
)
def test_given_missing_or_mistyped_subcommand_when_running_then_explains_update_syntax(
    test_case: SkillCommandTestCase,
) -> None:
    stdout: CaptureOutput = CaptureOutput()
    stderr: CaptureOutput = CaptureOutput()

    exit_code: int = run_skills(argv=test_case.argv, stdout=stdout, stderr=stderr)

    assert exit_code == test_case.expected_exit_code
    assert stdout.getvalue() == ""
    assert all(fragment in stderr.getvalue() for fragment in test_case.expected_output_fragments)


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
            expected_file_fragments=(
                "### Domain Shape",
                "Leaf domain:",
                "Branch domain:",
                "Domains may be leaves",
                "Do not mix the two shapes.",
                "prefer a leaf instead of creating a placeholder `core` subdomain",
                "Generic package names are banned",
                "src/pkg/<domain>[/<subdomain>]/",
            ),
            expected_absent_fragments=("## SFX002:", "Never use `core`"),
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
            expected_file_fragments=(
                "### Domain Shape",
                "Leaf domain:",
                "Branch domain:",
                "Domains may be leaves",
                "Do not mix the two shapes.",
                "prefer a leaf instead of creating a placeholder `core` subdomain",
                "Generic package names are banned",
                "src/pkg/<domain>[/<subdomain>]/",
            ),
            expected_absent_fragments=("## SFX002:", "Never use `core`"),
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
    active_rules: tuple[RuleSpec, ...] = build_ruleset(config=config)
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
        assert "## Repository Structure" in content
        assert "### Runtime" in content
        assert "### Tests" in content
        assert "## SFX001:" in content
        assert "## XCK001: always" in content
        assert "custom fault" in content
        assert all(heading in content for heading in active_rule_headings)
        assert all(fragment in content for fragment in test_case.expected_file_fragments)
        assert all(fragment not in content for fragment in test_case.expected_absent_fragments)


@pytest.mark.parametrize(
    "test_case",
    [
        SkillCommandTestCase(
            description="nested invocation writes repository-local skill at the config root",
            argv=("update", "--target", "agents"),
            expected_exit_code=0,
            expected_output_fragments=("Updated Strata skill files:",),
            expected_written_paths=(".agents/skills/strata/SKILL.md",),
        )
    ],
    ids=lambda case: case.description,
)
def test_given_nested_working_directory_when_updating_skills_then_writes_at_project_root(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    test_case: SkillCommandTestCase,
) -> None:
    write_cli_fixture_project(root=tmp_path, rule_code="XCK003", include_core_rules=True)
    nested: Path = tmp_path / "src/pkg/nested"
    nested.mkdir()
    monkeypatch.chdir(nested)
    stdout: CaptureOutput = CaptureOutput()

    exit_code: int = run_skills(argv=test_case.argv, stdout=stdout)

    assert exit_code == test_case.expected_exit_code
    assert all(fragment in stdout.getvalue() for fragment in test_case.expected_output_fragments)
    assert all((tmp_path / path).is_file() for path in test_case.expected_written_paths)
    assert not (nested / ".agents").exists()


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


@pytest.mark.parametrize(
    "test_case",
    [
        SkillCommandTestCase(
            description="later user-authored target prevents every default target write",
            argv=("update",),
            expected_exit_code=2,
            expected_output_fragments=("refusing to overwrite non-generated skill file",),
            expected_written_paths=(
                ".opencode/skills/strata/SKILL.md",
                ".claude/skills/strata/SKILL.md",
                ".agents/skills/strata/SKILL.md",
            ),
            expected_file_fragment=f"{GENERATED_MARKER}\nstale generated guidance\n",
        )
    ],
    ids=lambda case: case.description,
)
def test_given_later_user_skill_when_updating_all_targets_then_writes_nothing(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    test_case: SkillCommandTestCase,
) -> None:
    write_cli_fixture_project(root=tmp_path, rule_code="XCK001", include_core_rules=True)
    first_path: Path = tmp_path / test_case.expected_written_paths[0]
    first_path.parent.mkdir(parents=True)
    first_path.write_text(test_case.expected_file_fragment, encoding="utf-8")
    second_path: Path = tmp_path / test_case.expected_written_paths[1]
    second_path.parent.mkdir(parents=True)
    second_path.write_text("user-authored guidance\n", encoding="utf-8")
    third_path: Path = tmp_path / test_case.expected_written_paths[2]
    monkeypatch.chdir(tmp_path)
    stdout: CaptureOutput = CaptureOutput()
    stderr: CaptureOutput = CaptureOutput()

    exit_code: int = run_skills(argv=test_case.argv, stdout=stdout, stderr=stderr)

    assert exit_code == test_case.expected_exit_code
    combined_output: str = f"{stdout.getvalue()}{stderr.getvalue()}"
    assert all(fragment in combined_output for fragment in test_case.expected_output_fragments)
    assert first_path.read_text(encoding="utf-8") == test_case.expected_file_fragment
    assert second_path.read_text(encoding="utf-8") == "user-authored guidance\n"
    assert not third_path.exists()


@pytest.mark.parametrize(
    "test_case",
    [
        SkillCommandTestCase(
            description="symlinked opencode parent cannot escape the repository",
            argv=("update",),
            expected_exit_code=2,
            expected_output_fragments=("refusing to write unsafe skill target",),
            expected_written_paths=(
                ".opencode/skills/strata/SKILL.md",
                ".claude/skills/strata/SKILL.md",
                ".agents/skills/strata/SKILL.md",
            ),
        )
    ],
    ids=lambda case: case.description,
)
def test_given_symlinked_agent_parent_when_updating_then_rejects_escape_without_writes(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    test_case: SkillCommandTestCase,
) -> None:
    write_cli_fixture_project(root=tmp_path, rule_code="XCK001", include_core_rules=True)
    escaped_directory: Path = tmp_path / "escaped"
    escaped_directory.mkdir()
    (tmp_path / ".opencode").symlink_to(escaped_directory, target_is_directory=True)
    monkeypatch.chdir(tmp_path)
    stderr: CaptureOutput = CaptureOutput()

    exit_code: int = run_skills(argv=test_case.argv, stderr=stderr)

    assert exit_code == test_case.expected_exit_code
    assert all(fragment in stderr.getvalue() for fragment in test_case.expected_output_fragments)
    assert not (escaped_directory / "skills").exists()
    assert not (tmp_path / test_case.expected_written_paths[1]).exists()
    assert not (tmp_path / test_case.expected_written_paths[2]).exists()


@pytest.mark.parametrize(
    "test_case",
    [
        SkillTransactionFailureTestCase(
            description="second replacement failure rolls back the first target",
            failure_at=2,
            expected_exit_code=2,
            expected_error_fragment="simulated skill replacement failure",
        ),
        SkillTransactionFailureTestCase(
            description="third replacement failure rolls back two targets",
            failure_at=3,
            expected_exit_code=2,
            expected_error_fragment="simulated skill replacement failure",
        ),
    ],
    ids=lambda case: case.description,
)
def test_given_write_time_failure_when_updating_then_restores_entire_target_set(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    test_case: SkillTransactionFailureTestCase,
) -> None:
    write_cli_fixture_project(root=tmp_path, rule_code="XCK001", include_core_rules=True)
    first_path: Path = tmp_path / ".opencode/skills/strata/SKILL.md"
    first_path.parent.mkdir(parents=True)
    first_content: str = f"{GENERATED_MARKER}\nold opencode guidance\n"
    first_path.write_text(first_content, encoding="utf-8")
    second_path: Path = tmp_path / ".claude/skills/strata/SKILL.md"
    third_path: Path = tmp_path / ".agents/skills/strata/SKILL.md"
    third_path.parent.mkdir(parents=True)
    third_content: str = f"{GENERATED_MARKER}\nold agents guidance\n"
    third_path.write_text(third_content, encoding="utf-8")
    publisher: FailingSkillPublisher = FailingSkillPublisher(
        failure_at=test_case.failure_at,
        publish=installation._publish_staged_file,
    )
    monkeypatch.setattr(installation, "_publish_staged_file", publisher)
    monkeypatch.chdir(tmp_path)
    stderr: CaptureOutput = CaptureOutput()

    exit_code: int = run_skills(argv=("update",), stderr=stderr)

    assert exit_code == test_case.expected_exit_code
    assert test_case.expected_error_fragment in stderr.getvalue()
    assert first_path.read_text(encoding="utf-8") == first_content
    assert not second_path.exists()
    assert third_path.read_text(encoding="utf-8") == third_content


@pytest.mark.parametrize(
    "test_case",
    [
        SkillTransactionFailureTestCase(
            description="user creates absent second target immediately before publication",
            failure_at=1,
            expected_exit_code=2,
            expected_error_fragment="failed to install skill files",
        )
    ],
    ids=lambda case: case.description,
)
def test_given_user_file_race_when_publishing_absent_target_then_preserves_user_file(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    test_case: SkillTransactionFailureTestCase,
) -> None:
    write_cli_fixture_project(root=tmp_path, rule_code="XCK001", include_core_rules=True)
    first_path: Path = tmp_path / ".opencode/skills/strata/SKILL.md"
    first_path.parent.mkdir(parents=True)
    first_content: str = f"{GENERATED_MARKER}\nold opencode guidance\n"
    first_path.write_text(first_content, encoding="utf-8")
    raced_path: Path = tmp_path / ".claude/skills/strata/SKILL.md"
    user_content: str = "user guidance created during publication\n"
    linker: RacingSkillLinker = RacingSkillLinker(
        race_at=test_case.failure_at,
        user_content=user_content,
        link=installation.os.link,
    )
    monkeypatch.setattr(installation.os, "link", linker)
    monkeypatch.chdir(tmp_path)
    stderr: CaptureOutput = CaptureOutput()

    exit_code: int = run_skills(argv=("update",), stderr=stderr)

    assert exit_code == test_case.expected_exit_code
    assert test_case.expected_error_fragment in stderr.getvalue()
    assert first_path.read_text(encoding="utf-8") == first_content
    assert raced_path.read_text(encoding="utf-8") == user_content
    assert not (tmp_path / ".agents/skills/strata/SKILL.md").exists()


@pytest.mark.parametrize(
    "test_case",
    [
        SkillTransactionFailureTestCase(
            description="user replaces existing second target after descriptor validation",
            failure_at=2,
            expected_exit_code=2,
            expected_error_fragment="skill target changed during update",
        )
    ],
    ids=lambda case: case.description,
)
def test_given_existing_target_race_when_publishing_then_preserves_user_replacement(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    test_case: SkillTransactionFailureTestCase,
) -> None:
    write_cli_fixture_project(root=tmp_path, rule_code="XCK001", include_core_rules=True)
    first_path: Path = tmp_path / ".opencode/skills/strata/SKILL.md"
    first_path.parent.mkdir(parents=True)
    first_content: str = f"{GENERATED_MARKER}\nold opencode guidance\n"
    first_path.write_text(first_content, encoding="utf-8")
    raced_path: Path = tmp_path / ".claude/skills/strata/SKILL.md"
    raced_path.parent.mkdir(parents=True)
    raced_path.write_text(f"{GENERATED_MARKER}\nold claude guidance\n", encoding="utf-8")
    user_content: str = "user replacement created during publication\n"
    writer: RacingExistingSkillWriter = RacingExistingSkillWriter(
        race_at=test_case.failure_at,
        target_path=raced_path,
        user_content=user_content,
        write=installation._write_skill_descriptor,
    )
    monkeypatch.setattr(installation, "_write_skill_descriptor", writer)
    monkeypatch.chdir(tmp_path)
    stderr: CaptureOutput = CaptureOutput()

    exit_code: int = run_skills(argv=("update",), stderr=stderr)

    assert exit_code == test_case.expected_exit_code
    assert test_case.expected_error_fragment in stderr.getvalue()
    assert first_path.read_text(encoding="utf-8") == first_content
    assert raced_path.read_text(encoding="utf-8") == user_content
    assert not (tmp_path / ".agents/skills/strata/SKILL.md").exists()
