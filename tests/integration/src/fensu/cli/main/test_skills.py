"""Tests for repository-aware skill installation."""

from __future__ import annotations

import os
import shutil
import stat
from collections.abc import Callable
from pathlib import Path

import pytest

from fensu.agentdocs._helpers import installation
from fensu.agentdocs._helpers.ownership import parse_skill_ownership
from fensu.agentdocs.constants import GENERATED_MARKER
from fensu.agentdocs.models import SkillOwnership
from fensu.cli.main._skills import run_skills
from fensu.config.main.load_config import load_config
from fensu.config.models import Config
from fensu.rules.authoring.models import RuleSpec
from fensu.rules.catalog.main.build_ruleset import build_ruleset
from tests.integration.src.fensu.cli.main._test_types import (
    SkillCommandTestCase,
    SkillFreshnessTestCase,
    SkillTransactionFailureTestCase,
)
from tests.integration.src.fensu.cli.main.helpers import (
    CaptureOutput,
    FailingSkillDeleter,
    FailingSkillPublisher,
    RacingExistingSkillWriter,
    RacingLegacyRenamer,
    RacingSkillLinker,
    complete_filesystem_snapshot,
    generated_skill_text,
    mutate_skill_freshness_state,
    write_cli_fixture_project,
    write_cli_warning_skill_project,
    write_project_skill_bundle,
)


@pytest.mark.parametrize(
    "test_case",
    [
        SkillCommandTestCase(
            description="bare command writes every repository-local target",
            argv=(),
            expected_exit_code=0,
            expected_output_fragments=("Updated Fensu skill files:",),
            expected_written_paths=(
                ".opencode/skills/fensu-fixture/SKILL.md",
                ".claude/skills/fensu-fixture/SKILL.md",
                ".agents/skills/fensu-fixture/SKILL.md",
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
            expected_absent_fragments=("### FFH002:", "Never use `core`"),
        ),
        SkillCommandTestCase(
            description="global target filter writes selected home locations",
            argv=("--global", "--target", "opencode", "--target", "agents"),
            expected_exit_code=0,
            expected_output_fragments=("Updated Fensu skill files:",),
            expected_written_paths=(
                "home/.config/opencode/skills/fensu-fixture/SKILL.md",
                "home/.agents/skills/fensu-fixture/SKILL.md",
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
            expected_absent_fragments=("### FFH002:", "Never use `core`"),
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
        f"### {rule.code}: {rule.slug}" for rule in active_rules
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
        assert "### FFH001:" in content
        assert "### XCK001: always" in content
        assert "custom fault" in content
        assert all(heading in content for heading in active_rule_headings)
        assert all(fragment in content for fragment in test_case.expected_file_fragments)
        assert all(fragment not in content for fragment in test_case.expected_absent_fragments)


@pytest.mark.parametrize(
    "test_case",
    [
        SkillCommandTestCase(
            description="warning selection installs distinct resolved policy tiers",
            argv=("--target", "agents"),
            expected_exit_code=0,
            expected_output_fragments=("Updated Fensu skill files:",),
            expected_written_paths=(".agents/skills/fensu-fixture/SKILL.md",),
            expected_file_fragments=(
                '- Blocking selectors (`select`): ["FFN001"]',
                '- Warning selectors (`warn`): ["XSK001"]',
                '- Ignore selectors (`ignore`): ["FFH002"]',
                '- Blocking rule codes: ["FFN001"]',
                '- Warning rule codes: ["XSK001"]',
                '- Ignored matched rule codes: ["FFH002"]',
                "## Blocking Rules",
                "### FFN001: validator-must-not-return",
                "## Warning Rules",
                "### XSK001: always",
                "custom fault",
            ),
        )
    ],
    ids=lambda case: case.description,
)
def test_given_warning_configuration_when_updating_then_installs_distinct_tier_details(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    test_case: SkillCommandTestCase,
) -> None:
    write_cli_warning_skill_project(root=tmp_path, rule_code="XSK001")
    monkeypatch.chdir(tmp_path)
    stdout: CaptureOutput = CaptureOutput()
    stderr: CaptureOutput = CaptureOutput()

    exit_code: int = run_skills(
        argv=test_case.argv,
        stdout=stdout,
        stderr=stderr,
    )
    content: str = (tmp_path / test_case.expected_written_paths[0]).read_text(encoding="utf-8")
    blocking_section: str = content.partition("## Blocking Rules")[2].partition("## Warning Rules")[
        0
    ]

    assert exit_code == test_case.expected_exit_code
    assert all(fragment in stdout.getvalue() for fragment in test_case.expected_output_fragments)
    assert stderr.getvalue() == ""
    assert all(fragment in content for fragment in test_case.expected_file_fragments)
    assert "### XSK001:" not in blocking_section


@pytest.mark.parametrize(
    "test_case",
    [
        SkillCommandTestCase(
            description="nested invocation writes repository-local skill at the config root",
            argv=("--target", "agents"),
            expected_exit_code=0,
            expected_output_fragments=("Updated Fensu skill files:",),
            expected_written_paths=(".agents/skills/fensu-fixture/SKILL.md",),
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
            argv=("--target", "agents"),
            expected_exit_code=2,
            expected_output_fragments=("refusing to overwrite unmanaged skill file",),
            expected_written_paths=(".agents/skills/fensu-fixture/SKILL.md",),
            expected_file_fragment="user-authored guidance",
        ),
        SkillCommandTestCase(
            description="force replaces a non-generated file",
            argv=("--target", "agents", "--force"),
            expected_exit_code=0,
            expected_output_fragments=("Updated Fensu skill files:",),
            expected_written_paths=(".agents/skills/fensu-fixture/SKILL.md",),
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
            argv=(),
            expected_exit_code=2,
            expected_output_fragments=("refusing to overwrite unmanaged skill file",),
            expected_written_paths=(
                ".opencode/skills/fensu-fixture/SKILL.md",
                ".claude/skills/fensu-fixture/SKILL.md",
                ".agents/skills/fensu-fixture/SKILL.md",
            ),
            expected_file_fragment="stale generated guidance\n",
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
    first_content: str = generated_skill_text(root=tmp_path, body=test_case.expected_file_fragment)
    first_path.write_text(first_content, encoding="utf-8")
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
    assert first_path.read_text(encoding="utf-8") == first_content
    assert second_path.read_text(encoding="utf-8") == "user-authored guidance\n"
    assert not third_path.exists()


@pytest.mark.parametrize(
    "test_case",
    [
        SkillCommandTestCase(
            description="symlinked opencode parent cannot escape the repository",
            argv=(),
            expected_exit_code=2,
            expected_output_fragments=("refusing to write unsafe skill target",),
            expected_written_paths=(
                ".opencode/skills/fensu-fixture/SKILL.md",
                ".claude/skills/fensu-fixture/SKILL.md",
                ".agents/skills/fensu-fixture/SKILL.md",
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
    first_path: Path = tmp_path / ".opencode/skills/fensu-fixture/SKILL.md"
    first_path.parent.mkdir(parents=True)
    first_content: str = generated_skill_text(root=tmp_path, body="old opencode guidance\n")
    first_path.write_text(first_content, encoding="utf-8")
    second_path: Path = tmp_path / ".claude/skills/fensu-fixture/SKILL.md"
    third_path: Path = tmp_path / ".agents/skills/fensu-fixture/SKILL.md"
    third_path.parent.mkdir(parents=True)
    third_content: str = generated_skill_text(root=tmp_path, body="old agents guidance\n")
    third_path.write_text(third_content, encoding="utf-8")
    publisher: FailingSkillPublisher = FailingSkillPublisher(
        failure_at=test_case.failure_at,
        publish=installation._publish_staged_file,
    )
    monkeypatch.setattr(installation, "_publish_staged_file", publisher)
    monkeypatch.chdir(tmp_path)
    stderr: CaptureOutput = CaptureOutput()

    exit_code: int = run_skills(argv=(), stderr=stderr)

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
    first_path: Path = tmp_path / ".opencode/skills/fensu-fixture/SKILL.md"
    first_path.parent.mkdir(parents=True)
    first_content: str = generated_skill_text(root=tmp_path, body="old opencode guidance\n")
    first_path.write_text(first_content, encoding="utf-8")
    raced_path: Path = tmp_path / ".claude/skills/fensu-fixture/SKILL.md"
    user_content: str = "user guidance created during publication\n"
    linker: RacingSkillLinker = RacingSkillLinker(
        race_at=test_case.failure_at,
        user_content=user_content,
        link=installation.os.link,
    )
    monkeypatch.setattr(installation.os, "link", linker)
    monkeypatch.chdir(tmp_path)
    stderr: CaptureOutput = CaptureOutput()

    exit_code: int = run_skills(argv=(), stderr=stderr)

    assert exit_code == test_case.expected_exit_code
    assert test_case.expected_error_fragment in stderr.getvalue()
    assert first_path.read_text(encoding="utf-8") == first_content
    assert raced_path.read_text(encoding="utf-8") == user_content
    assert not (tmp_path / ".agents/skills/fensu-fixture/SKILL.md").exists()


@pytest.mark.parametrize(
    "test_case",
    [
        SkillCommandTestCase(
            description="default local update installs at parent Git root",
            argv=("--target", "agents"),
            expected_exit_code=0,
            expected_output_fragments=("Updated Fensu skill files:",),
            expected_written_paths=(".agents/skills/fensu-fixture/SKILL.md",),
            expected_file_fragments=(
                'Configuration source: "backend/fensu.toml"',
                '- Project root from installation root: "backend"',
                '- Product roots: ["backend/src/pkg"]',
                "backend/src/pkg/",
            ),
        ),
        SkillCommandTestCase(
            description="explicit Git keyword installs at parent Git root",
            argv=("--target", "agents", "--install-root", "git"),
            expected_exit_code=0,
            expected_output_fragments=("Updated Fensu skill files:",),
            expected_written_paths=(".agents/skills/fensu-fixture/SKILL.md",),
        ),
        SkillCommandTestCase(
            description="project keyword installs at Fensu config root",
            argv=("--target", "agents", "--install-root", "project"),
            expected_exit_code=0,
            expected_output_fragments=("Updated Fensu skill files:",),
            expected_written_paths=("backend/.agents/skills/fensu-fixture/SKILL.md",),
        ),
        SkillCommandTestCase(
            description="relative explicit path resolves from invocation directory",
            argv=("--target", "agents", "--install-root", "../custom"),
            expected_exit_code=0,
            expected_output_fragments=("Updated Fensu skill files:",),
            expected_written_paths=("custom/.agents/skills/fensu-fixture/SKILL.md",),
        ),
    ],
    ids=lambda case: case.description,
)
def test_given_monorepo_and_install_root_when_updating_then_resolves_expected_target_and_paths(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    test_case: SkillCommandTestCase,
) -> None:
    (tmp_path / ".git").mkdir()
    project: Path = tmp_path / "backend"
    project.mkdir()
    write_cli_fixture_project(root=project, rule_code="XIR001", include_core_rules=True)
    monkeypatch.chdir(project)
    stdout: CaptureOutput = CaptureOutput()
    stderr: CaptureOutput = CaptureOutput()

    exit_code: int = run_skills(argv=test_case.argv, stdout=stdout, stderr=stderr)
    content: str = (tmp_path / test_case.expected_written_paths[0]).read_text(encoding="utf-8")

    assert exit_code == test_case.expected_exit_code
    assert stderr.getvalue() == ""
    assert all(fragment in stdout.getvalue() for fragment in test_case.expected_output_fragments)
    assert all(fragment in content for fragment in test_case.expected_file_fragments)


@pytest.mark.parametrize(
    "test_case",
    [
        SkillCommandTestCase(
            description="global and install-root options are explicitly incompatible",
            argv=("--global", "--install-root", "project"),
            expected_exit_code=2,
            expected_output_fragments=("--install-root cannot be combined with --global",),
        )
    ],
    ids=lambda case: case.description,
)
def test_given_global_and_install_root_when_updating_then_rejects_ambiguous_scope(
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
            description="repeated identical targets are deterministically deduplicated",
            argv=("--target", "agents", "--target", "agents"),
            expected_exit_code=0,
            expected_output_fragments=("Updated Fensu skill files:",),
            expected_written_paths=(".agents/skills/fensu-fixture/SKILL.md",),
        )
    ],
    ids=lambda case: case.description,
)
def test_given_repeated_target_when_updating_then_writes_target_once(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    test_case: SkillCommandTestCase,
) -> None:
    write_cli_fixture_project(root=tmp_path, rule_code="XDT001")
    monkeypatch.chdir(tmp_path)
    stdout: CaptureOutput = CaptureOutput()

    exit_code: int = run_skills(argv=test_case.argv, stdout=stdout)

    assert exit_code == test_case.expected_exit_code
    assert stdout.getvalue().count("SKILL.md") == len(test_case.expected_written_paths)
    assert (tmp_path / test_case.expected_written_paths[0]).is_file()


@pytest.mark.parametrize(
    "test_case",
    [
        SkillCommandTestCase(
            description="generated file carries complete structured ownership metadata",
            argv=("--target", "agents"),
            expected_exit_code=0,
            expected_output_fragments=("Updated Fensu skill files:",),
            expected_written_paths=(".agents/skills/fensu-fixture/SKILL.md",),
            expected_file_fragments=("fensu-skill-owner",),
        )
    ],
    ids=lambda case: case.description,
)
def test_given_project_update_when_installing_then_embeds_structured_ownership_marker(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    test_case: SkillCommandTestCase,
) -> None:
    write_cli_fixture_project(root=tmp_path, rule_code="XOM001")
    monkeypatch.chdir(tmp_path)

    exit_code: int = run_skills(argv=test_case.argv)
    path: Path = tmp_path / test_case.expected_written_paths[0]
    content: bytes = path.read_bytes()
    ownership: SkillOwnership | None = parse_skill_ownership(content)

    assert exit_code == test_case.expected_exit_code
    assert ownership is not None
    assert ownership.schema == 1
    assert ownership.identity == "fensu-fixture"
    assert len(ownership.owner) == 64
    assert len(ownership.input_fingerprint) == 64
    assert len(ownership.content_fingerprint) == 64
    assert ownership.input_fingerprint != ownership.content_fingerprint
    assert all(fragment.encode() in content for fragment in test_case.expected_file_fragments)


@pytest.mark.parametrize(
    "test_case",
    [
        SkillCommandTestCase(
            description="force cannot overwrite a same-name skill owned by another project",
            argv=("--target", "agents", "--install-root", "../shared", "--force"),
            expected_exit_code=2,
            expected_output_fragments=("owned by another Fensu project",),
            expected_written_paths=("shared/.agents/skills/fensu-fixture/SKILL.md",),
        )
    ],
    ids=lambda case: case.description,
)
def test_given_foreign_owner_collision_when_forcing_then_preserves_existing_project_skill(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    test_case: SkillCommandTestCase,
) -> None:
    first_project: Path = tmp_path / "first"
    second_project: Path = tmp_path / "second"
    first_project.mkdir()
    second_project.mkdir()
    write_cli_fixture_project(root=first_project, rule_code="XFO001")
    write_cli_fixture_project(root=second_project, rule_code="XFO002")
    monkeypatch.chdir(first_project)
    first_exit: int = run_skills(argv=("--target", "agents", "--install-root", "../shared"))
    target: Path = tmp_path / test_case.expected_written_paths[0]
    original: bytes = target.read_bytes()
    monkeypatch.chdir(second_project)
    stderr: CaptureOutput = CaptureOutput()

    exit_code: int = run_skills(argv=test_case.argv, stderr=stderr)

    assert first_exit == 0
    assert exit_code == test_case.expected_exit_code
    assert all(fragment in stderr.getvalue() for fragment in test_case.expected_output_fragments)
    assert target.read_bytes() == original


@pytest.mark.parametrize(
    "test_case",
    [
        SkillCommandTestCase(
            description="case-only normalized directory collision is rejected even with force",
            argv=("--target", "agents", "--force"),
            expected_exit_code=2,
            expected_output_fragments=("identity normalization collides",),
            expected_written_paths=(".agents/skills/Fensu-Fixture/user.txt",),
        )
    ],
    ids=lambda case: case.description,
)
def test_given_case_colliding_skill_directory_when_updating_then_preserves_existing_path(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    test_case: SkillCommandTestCase,
) -> None:
    write_cli_fixture_project(root=tmp_path, rule_code="XNC001")
    existing: Path = tmp_path / test_case.expected_written_paths[0]
    existing.parent.mkdir(parents=True)
    existing.write_text("user file\n", encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    stderr: CaptureOutput = CaptureOutput()

    exit_code: int = run_skills(argv=test_case.argv, stderr=stderr)

    assert exit_code == test_case.expected_exit_code
    assert all(fragment in stderr.getvalue() for fragment in test_case.expected_output_fragments)
    assert existing.read_text(encoding="utf-8") == "user file\n"


@pytest.mark.parametrize(
    "test_case",
    [
        SkillCommandTestCase(
            description="marker-owned generic skill migrates while user sibling remains",
            argv=("--target", "agents"),
            expected_exit_code=0,
            expected_output_fragments=("Updated Fensu skill files:",),
            expected_written_paths=(
                ".agents/skills/fensu/SKILL.md",
                ".agents/skills/fensu/notes.txt",
                ".agents/skills/fensu-fixture/SKILL.md",
            ),
        )
    ],
    ids=lambda case: case.description,
)
def test_given_owned_generic_skill_when_updating_then_migrates_without_recursive_deletion(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    test_case: SkillCommandTestCase,
) -> None:
    write_cli_fixture_project(root=tmp_path, rule_code="XMG001")
    generic: Path = tmp_path / test_case.expected_written_paths[0]
    user_file: Path = tmp_path / test_case.expected_written_paths[1]
    generic.parent.mkdir(parents=True)
    generic.write_text(f"{GENERATED_MARKER}\nlegacy\n", encoding="utf-8")
    user_file.write_text("keep me\n", encoding="utf-8")
    monkeypatch.chdir(tmp_path)

    exit_code: int = run_skills(argv=test_case.argv)

    assert exit_code == test_case.expected_exit_code
    assert not generic.exists()
    assert user_file.read_text(encoding="utf-8") == "keep me\n"
    assert (tmp_path / test_case.expected_written_paths[2]).is_file()


@pytest.mark.parametrize(
    "test_case",
    [
        SkillCommandTestCase(
            description="unmanaged generic skill is never migrated",
            argv=("--target", "agents"),
            expected_exit_code=0,
            expected_output_fragments=("Updated Fensu skill files:",),
            expected_written_paths=(".agents/skills/fensu/SKILL.md",),
            expected_file_fragment="user-authored generic skill\n",
        ),
        SkillCommandTestCase(
            description="symlink generic skill aborts migration without publishing",
            argv=("--target", "agents"),
            expected_exit_code=2,
            expected_output_fragments=("unsafe skill target",),
            expected_written_paths=(".agents/skills/fensu/SKILL.md",),
            expected_file_fragment="symlink",
        ),
    ],
    ids=lambda case: case.description,
)
def test_given_unmanaged_or_symlink_generic_skill_when_updating_then_never_deletes_it(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    test_case: SkillCommandTestCase,
) -> None:
    write_cli_fixture_project(root=tmp_path, rule_code="XPS001")
    generic: Path = tmp_path / test_case.expected_written_paths[0]
    generic.parent.mkdir(parents=True)
    outside: Path = tmp_path / "outside-skill"
    outside.write_text("outside\n", encoding="utf-8")
    writers: dict[str, Callable[[], object]] = {
        "symlink": lambda: generic.symlink_to(outside),
        "user-authored generic skill\n": lambda: generic.write_text(
            test_case.expected_file_fragment, encoding="utf-8"
        ),
    }
    _ = writers[test_case.expected_file_fragment]()
    monkeypatch.chdir(tmp_path)
    stdout: CaptureOutput = CaptureOutput()
    stderr: CaptureOutput = CaptureOutput()

    exit_code: int = run_skills(argv=test_case.argv, stdout=stdout, stderr=stderr)
    combined: str = stdout.getvalue() + stderr.getvalue()

    assert exit_code == test_case.expected_exit_code
    assert all(fragment in combined for fragment in test_case.expected_output_fragments)
    assert generic.exists()


@pytest.mark.parametrize(
    "test_case",
    [
        SkillTransactionFailureTestCase(
            description="later legacy deletion failure restores earlier deletion and new targets",
            failure_at=2,
            expected_exit_code=2,
            expected_error_fragment="simulated legacy deletion failure",
        )
    ],
    ids=lambda case: case.description,
)
def test_given_legacy_deletion_failure_when_migrating_then_rolls_back_whole_transaction(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    test_case: SkillTransactionFailureTestCase,
) -> None:
    write_cli_fixture_project(root=tmp_path, rule_code="XRB001")
    first: Path = tmp_path / ".opencode/skills/fensu/SKILL.md"
    second: Path = tmp_path / ".claude/skills/fensu/SKILL.md"
    first.parent.mkdir(parents=True)
    second.parent.mkdir(parents=True)
    legacy_content: str = f"{GENERATED_MARKER}\nlegacy\n"
    first.write_text(legacy_content, encoding="utf-8")
    second.write_text(legacy_content, encoding="utf-8")
    deleter: FailingSkillDeleter = FailingSkillDeleter(
        failure_at=test_case.failure_at,
        delete=installation._publish_skill_deletion,
    )
    monkeypatch.setattr(installation, "_publish_skill_deletion", deleter)
    monkeypatch.chdir(tmp_path)
    stderr: CaptureOutput = CaptureOutput()

    exit_code: int = run_skills(argv=(), stderr=stderr)

    assert exit_code == test_case.expected_exit_code
    assert test_case.expected_error_fragment in stderr.getvalue()
    assert first.read_text(encoding="utf-8") == legacy_content
    assert second.read_text(encoding="utf-8") == legacy_content
    assert not (tmp_path / ".agents/skills/fensu-fixture/SKILL.md").exists()


@pytest.mark.parametrize(
    "test_case",
    [
        SkillTransactionFailureTestCase(
            description="legacy replacement race preserves user file and rolls back new target",
            failure_at=1,
            expected_exit_code=2,
            expected_error_fragment="legacy skill target changed during migration",
        )
    ],
    ids=lambda case: case.description,
)
def test_given_legacy_replacement_race_when_migrating_then_preserves_user_replacement(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    test_case: SkillTransactionFailureTestCase,
) -> None:
    write_cli_fixture_project(root=tmp_path, rule_code="XRC001")
    legacy: Path = tmp_path / ".agents/skills/fensu/SKILL.md"
    legacy.parent.mkdir(parents=True)
    legacy.write_text(f"{GENERATED_MARKER}\nlegacy\n", encoding="utf-8")
    user_content: str = "user replacement\n"
    renamer: RacingLegacyRenamer = RacingLegacyRenamer(
        legacy_path=legacy,
        user_content=user_content,
        rename=Path.rename,
    )
    monkeypatch.setattr(Path, "rename", lambda source, target: renamer(source, target))
    monkeypatch.chdir(tmp_path)
    stderr: CaptureOutput = CaptureOutput()

    exit_code: int = run_skills(
        argv=("--target", "agents"),
        stderr=stderr,
    )

    assert exit_code == test_case.expected_exit_code
    assert test_case.expected_error_fragment in stderr.getvalue()
    assert legacy.read_text(encoding="utf-8") == user_content
    assert not (tmp_path / ".agents/skills/fensu-fixture/SKILL.md").exists()


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
@pytest.mark.skipif(os.name == "nt", reason="Windows prevents replacing an open file")
def test_given_existing_target_race_when_publishing_then_preserves_user_replacement(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    test_case: SkillTransactionFailureTestCase,
) -> None:
    write_cli_fixture_project(root=tmp_path, rule_code="XCK001", include_core_rules=True)
    first_path: Path = tmp_path / ".opencode/skills/fensu-fixture/SKILL.md"
    first_path.parent.mkdir(parents=True)
    first_content: str = generated_skill_text(root=tmp_path, body="old opencode guidance\n")
    first_path.write_text(first_content, encoding="utf-8")
    raced_path: Path = tmp_path / ".claude/skills/fensu-fixture/SKILL.md"
    raced_path.parent.mkdir(parents=True)
    raced_path.write_text(
        generated_skill_text(root=tmp_path, body="old claude guidance\n"),
        encoding="utf-8",
    )
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

    exit_code: int = run_skills(argv=(), stderr=stderr)

    assert exit_code == test_case.expected_exit_code
    assert test_case.expected_error_fragment in stderr.getvalue()
    assert first_path.read_text(encoding="utf-8") == first_content
    assert raced_path.read_text(encoding="utf-8") == user_content
    assert not (tmp_path / ".agents/skills/fensu-fixture/SKILL.md").exists()


@pytest.mark.parametrize(
    "test_case",
    [
        SkillFreshnessTestCase(
            description="current deterministic bytes return zero",
            state="current",
            expected_exit_code=0,
            expected_reason="current",
        ),
        SkillFreshnessTestCase(
            description="missing expected generated file returns one",
            state="missing",
            expected_exit_code=1,
            expected_reason="missing",
        ),
        SkillFreshnessTestCase(
            description="effective policy drift returns stale",
            state="stale",
            expected_exit_code=1,
            expected_reason="stale",
        ),
        SkillFreshnessTestCase(
            description="manual byte modification returns divergent",
            state="divergent",
            expected_exit_code=1,
            expected_reason="divergent",
        ),
        SkillFreshnessTestCase(
            description="invalid structured ownership returns malformed marker",
            state="malformed-marker",
            expected_exit_code=1,
            expected_reason="malformed-marker",
        ),
        SkillFreshnessTestCase(
            description="occupied unmanaged target returns collision error",
            state="collision",
            expected_exit_code=2,
            expected_reason="collision",
        ),
    ],
    ids=lambda case: case.description,
)
def test_given_expected_target_state_when_checking_update_then_reports_exact_reason_without_writes(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    test_case: SkillFreshnessTestCase,
) -> None:
    write_cli_fixture_project(root=tmp_path, rule_code="XFR001")
    monkeypatch.chdir(tmp_path)
    installed: int = run_skills(argv=("--target", "agents"))
    mutate_skill_freshness_state(root=tmp_path, state=test_case.state)
    before: tuple[tuple[str, str, int, int, bytes], ...] = complete_filesystem_snapshot(tmp_path)
    stdout: CaptureOutput = CaptureOutput()
    stderr: CaptureOutput = CaptureOutput()

    exit_code: int = run_skills(
        argv=("--target", "agents", "--check"),
        stdout=stdout,
        stderr=stderr,
    )
    after: tuple[tuple[str, str, int, int, bytes], ...] = complete_filesystem_snapshot(tmp_path)
    target: Path = tmp_path / ".agents/skills/fensu-fixture/SKILL.md"
    rendered_target: str = target.as_posix()
    expected_output: str = {
        "current": f"Fensu skill files are current:\n  {rendered_target}\n",
    }.get(
        test_case.expected_reason,
        f"Fensu skill files require update:\n  {rendered_target}: {test_case.expected_reason}\n",
    )

    assert installed == 0
    assert exit_code == test_case.expected_exit_code
    assert stdout.getvalue() == expected_output
    assert stderr.getvalue() == ""
    assert after == before


@pytest.mark.parametrize(
    "test_case",
    [
        SkillCommandTestCase(
            description="check rejects force before loading or writing project state",
            argv=("--check", "--force"),
            expected_exit_code=2,
            expected_output_fragments=("--check cannot be combined with --force.",),
        )
    ],
    ids=lambda case: case.description,
)
def test_given_check_and_force_when_running_skills_then_rejects_write_only_option(
    tmp_path: Path,
    test_case: SkillCommandTestCase,
) -> None:
    before: tuple[tuple[str, str, int, int, bytes], ...] = complete_filesystem_snapshot(tmp_path)
    stdout: CaptureOutput = CaptureOutput()
    stderr: CaptureOutput = CaptureOutput()

    exit_code: int = run_skills(argv=test_case.argv, stdout=stdout, stderr=stderr)

    assert exit_code == test_case.expected_exit_code
    assert stdout.getvalue() == ""
    assert all(fragment in stderr.getvalue() for fragment in test_case.expected_output_fragments)
    assert complete_filesystem_snapshot(tmp_path) == before


@pytest.mark.parametrize(
    "test_case",
    [
        SkillCommandTestCase(
            description="all absent defaults are reported in path order",
            argv=("--check",),
            expected_exit_code=1,
            expected_output_fragments=(
                ".agents/skills/fensu-fixture/SKILL.md: missing",
                ".claude/skills/fensu-fixture/SKILL.md: missing",
                ".opencode/skills/fensu-fixture/SKILL.md: missing",
            ),
        )
    ],
    ids=lambda case: case.description,
)
def test_given_multiple_missing_targets_when_checking_then_reports_deterministic_path_order(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    test_case: SkillCommandTestCase,
) -> None:
    write_cli_fixture_project(root=tmp_path, rule_code="XFR002")
    monkeypatch.chdir(tmp_path)
    stdout: CaptureOutput = CaptureOutput()

    exit_code: int = run_skills(argv=test_case.argv, stdout=stdout)
    output: str = stdout.getvalue()

    assert exit_code == test_case.expected_exit_code
    assert all(fragment in output for fragment in test_case.expected_output_fragments)
    assert output.index(".agents/") < output.index(".claude/") < output.index(".opencode/")


@pytest.mark.parametrize(
    "test_case",
    [
        SkillCommandTestCase(
            description="multiple canonical bundles copy nested text and binary files to defaults",
            argv=(),
            expected_exit_code=0,
            expected_output_fragments=("Updated Fensu skill files:",),
            expected_written_paths=(
                ".opencode/skills",
                ".claude/skills",
                ".agents/skills",
            ),
            expected_file_fragments=("synchronized-project-skill-by: fensu skills",),
            expected_absent_fragments=("generated-by: fensu skills update",),
        )
    ],
    ids=lambda case: case.description,
)
def test_given_canonical_project_bundles_when_updating_then_synchronizes_complete_default_targets(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    test_case: SkillCommandTestCase,
) -> None:
    write_cli_fixture_project(root=tmp_path, rule_code="XPB001")
    alpha_document: str = "---\nname: alpha\n---\n\n# Alpha\n"
    beta_document: str = "# Beta\n"
    binary_content: bytes = b"\x00\xff\x10binary\n"
    alpha_source: Path = write_project_skill_bundle(
        root=tmp_path,
        identity="alpha",
        document=alpha_document,
        support_files={
            "assets/logo.bin": binary_content,
            "references/nested/guide.txt": b"nested guidance\n",
        },
    )
    (alpha_source / "assets/logo.bin").chmod(0o750)
    _ = write_project_skill_bundle(
        root=tmp_path,
        identity="beta",
        document=beta_document,
        support_files={},
    )
    monkeypatch.chdir(tmp_path)
    stdout: CaptureOutput = CaptureOutput()

    exit_code: int = run_skills(argv=test_case.argv, stdout=stdout)

    assert exit_code == test_case.expected_exit_code
    assert all(fragment in stdout.getvalue() for fragment in test_case.expected_output_fragments)
    for skills_root in test_case.expected_written_paths:
        alpha: Path = tmp_path / skills_root / "alpha"
        beta: Path = tmp_path / skills_root / "beta"
        copied_document: str = (alpha / "SKILL.md").read_text(encoding="utf-8")
        ownership: SkillOwnership | None = parse_skill_ownership(copied_document.encode("utf-8"))
        assert copied_document.startswith(alpha_document)
        assert all(fragment in copied_document for fragment in test_case.expected_file_fragments)
        assert all(
            fragment not in copied_document for fragment in test_case.expected_absent_fragments
        )
        assert ownership is not None
        assert ownership.identity == "alpha"
        assert (alpha / "assets/logo.bin").read_bytes() == binary_content
        assert stat.S_IMODE((alpha / "assets/logo.bin").stat().st_mode) == stat.S_IMODE(
            (alpha_source / "assets/logo.bin").stat().st_mode
        )
        assert (alpha / "references/nested/guide.txt").read_bytes() == b"nested guidance\n"
        assert (beta / "SKILL.md").read_text(encoding="utf-8").startswith(beta_document)
    assert (tmp_path / ".ai/knowledge/repo/skills/alpha/SKILL.md").read_text(
        encoding="utf-8"
    ) == alpha_document


@pytest.mark.parametrize(
    "test_case",
    [
        SkillCommandTestCase(
            description="selected project-root target does not publish other agents",
            argv=("--target", "agents", "--install-root", "project"),
            expected_exit_code=0,
            expected_output_fragments=("Updated Fensu skill files:",),
            expected_written_paths=("backend/.agents/skills/alpha/SKILL.md",),
        )
    ],
    ids=lambda case: case.description,
)
def test_given_project_bundle_and_target_filter_when_updating_then_uses_selected_root_semantics(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    test_case: SkillCommandTestCase,
) -> None:
    (tmp_path / ".git").mkdir()
    project: Path = tmp_path / "backend"
    project.mkdir()
    write_cli_fixture_project(root=project, rule_code="XPB002")
    _ = write_project_skill_bundle(
        root=project,
        identity="alpha",
        document="# Alpha\n",
        support_files={},
    )
    monkeypatch.chdir(project)

    exit_code: int = run_skills(argv=test_case.argv)

    assert exit_code == test_case.expected_exit_code
    assert all((tmp_path / path).is_file() for path in test_case.expected_written_paths)
    assert not (project / ".opencode").exists()
    assert not (project / ".claude").exists()
    assert not (tmp_path / ".agents").exists()


@pytest.mark.parametrize(
    "test_case",
    [
        SkillCommandTestCase(
            description="unmanaged project destination blocks generated publication",
            argv=("--target", "agents"),
            expected_exit_code=2,
            expected_output_fragments=("refusing to overwrite unmanaged skill file",),
            expected_file_fragment="user-authored project skill\n",
        ),
        SkillCommandTestCase(
            description="force replaces unmanaged project destination as a whole bundle",
            argv=("--target", "agents", "--force"),
            expected_exit_code=0,
            expected_output_fragments=("Updated Fensu skill files:",),
            expected_file_fragment="# Canonical Alpha\n",
        ),
    ],
    ids=lambda case: case.description,
)
def test_given_unmanaged_project_destination_when_updating_then_requires_force_before_any_write(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    test_case: SkillCommandTestCase,
) -> None:
    write_cli_fixture_project(root=tmp_path, rule_code="XPB003")
    _ = write_project_skill_bundle(
        root=tmp_path,
        identity="alpha",
        document="# Canonical Alpha\n",
        support_files={},
    )
    destination: Path = tmp_path / ".agents/skills/alpha/SKILL.md"
    destination.parent.mkdir(parents=True)
    destination.write_text("user-authored project skill\n", encoding="utf-8")
    (destination.parent / "user-note.txt").write_text("remove only with force\n", encoding="utf-8")
    generated: Path = tmp_path / ".agents/skills/fensu-fixture/SKILL.md"
    monkeypatch.chdir(tmp_path)
    stdout: CaptureOutput = CaptureOutput()
    stderr: CaptureOutput = CaptureOutput()

    exit_code: int = run_skills(
        argv=test_case.argv,
        stdout=stdout,
        stderr=stderr,
    )

    assert exit_code == test_case.expected_exit_code
    assert all(
        fragment in stdout.getvalue() + stderr.getvalue()
        for fragment in test_case.expected_output_fragments
    )
    assert test_case.expected_file_fragment in destination.read_text(encoding="utf-8")
    assert generated.exists() == (test_case.expected_exit_code == 0)
    assert (destination.parent / "user-note.txt").exists() == (test_case.expected_exit_code != 0)


@pytest.mark.parametrize(
    "test_case",
    [
        SkillCommandTestCase(
            description="removed canonical bundle deletes only its same-owner installed copy",
            argv=("--target", "agents"),
            expected_exit_code=0,
            expected_output_fragments=("Updated Fensu skill files:",),
            expected_written_paths=(".agents/skills/alpha",),
        )
    ],
    ids=lambda case: case.description,
)
def test_given_removed_canonical_bundle_when_updating_then_removes_stale_owned_bundle(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    test_case: SkillCommandTestCase,
) -> None:
    write_cli_fixture_project(root=tmp_path, rule_code="XPB004")
    canonical: Path = write_project_skill_bundle(
        root=tmp_path,
        identity="alpha",
        document="# Alpha\n",
        support_files={"nested/data.bin": b"stale\x00"},
    )
    foreign: Path = tmp_path / ".agents/skills/unmanaged/SKILL.md"
    foreign.parent.mkdir(parents=True)
    foreign.write_text("user skill\n", encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    installed: int = run_skills(argv=test_case.argv)
    shutil.rmtree(canonical)

    exit_code: int = run_skills(argv=test_case.argv)

    assert installed == test_case.expected_exit_code
    assert exit_code == test_case.expected_exit_code
    assert not (tmp_path / test_case.expected_written_paths[0]).exists()
    assert foreign.read_text(encoding="utf-8") == "user skill\n"
    assert (tmp_path / ".agents/skills/fensu-fixture/SKILL.md").is_file()


@pytest.mark.parametrize(
    "test_case",
    [
        SkillFreshnessTestCase(
            description="binary project bundle drift is reported without writes",
            state="project-binary-divergent",
            expected_exit_code=1,
            expected_reason="divergent",
        )
    ],
    ids=lambda case: case.description,
)
def test_given_project_bundle_drift_when_checking_then_reports_file_without_writes(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    test_case: SkillFreshnessTestCase,
) -> None:
    write_cli_fixture_project(root=tmp_path, rule_code="XPB005")
    _ = write_project_skill_bundle(
        root=tmp_path,
        identity="alpha",
        document="# Alpha\n",
        support_files={"assets/data.bin": b"canonical\x00"},
    )
    monkeypatch.chdir(tmp_path)
    installed: int = run_skills(argv=("--target", "agents"))
    target: Path = tmp_path / ".agents/skills/alpha/assets/data.bin"
    target.write_bytes(b"modified\xff")
    before: tuple[tuple[str, str, int, int, bytes], ...] = complete_filesystem_snapshot(tmp_path)
    stdout: CaptureOutput = CaptureOutput()

    exit_code: int = run_skills(
        argv=("--target", "agents", "--check"),
        stdout=stdout,
    )

    assert installed == 0
    assert exit_code == test_case.expected_exit_code
    assert f"{target.as_posix()}: {test_case.expected_reason}" in stdout.getvalue()
    assert complete_filesystem_snapshot(tmp_path) == before


@pytest.mark.parametrize(
    "test_case",
    [
        SkillCommandTestCase(
            description="canonical support symlink rejects every selected destination",
            argv=(),
            expected_exit_code=2,
            expected_output_fragments=("project skill content cannot be a symlink",),
        ),
        SkillCommandTestCase(
            description="project identity colliding with generated guidance is rejected",
            argv=(),
            expected_exit_code=2,
            expected_output_fragments=("duplicate normalized skill identity",),
        ),
    ],
    ids=lambda case: case.description,
)
def test_given_unsafe_or_duplicate_canonical_bundle_when_updating_then_writes_nothing(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    test_case: SkillCommandTestCase,
) -> None:
    write_cli_fixture_project(root=tmp_path, rule_code="XPB006")
    bundle: Path = write_project_skill_bundle(
        root=tmp_path,
        identity={
            "canonical support symlink rejects every selected destination": "alpha",
            "project identity colliding with generated guidance is rejected": "fensu-fixture",
        }[test_case.description],
        document="# Skill\n",
        support_files={},
    )
    actions: dict[str, Callable[[], object]] = {
        "canonical support symlink rejects every selected destination": lambda: (
            bundle / "escape"
        ).symlink_to(tmp_path / "fensu.toml"),
        "project identity colliding with generated guidance is rejected": lambda: None,
    }
    _ = actions[test_case.description]()
    monkeypatch.chdir(tmp_path)
    stderr: CaptureOutput = CaptureOutput()

    exit_code: int = run_skills(argv=test_case.argv, stderr=stderr)

    assert exit_code == test_case.expected_exit_code
    assert all(fragment in stderr.getvalue() for fragment in test_case.expected_output_fragments)
    assert not (tmp_path / ".opencode").exists()
    assert not (tmp_path / ".claude").exists()
    assert not (tmp_path / ".agents").exists()


@pytest.mark.parametrize(
    "test_case",
    [
        SkillTransactionFailureTestCase(
            description="project binary publication failure restores generated and bundle targets",
            failure_at=3,
            expected_exit_code=2,
            expected_error_fragment="simulated skill replacement failure",
        )
    ],
    ids=lambda case: case.description,
)
def test_given_project_bundle_publication_failure_when_updating_then_rolls_back_all_files_and_roots(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    test_case: SkillTransactionFailureTestCase,
) -> None:
    write_cli_fixture_project(root=tmp_path, rule_code="XPB007")
    _ = write_project_skill_bundle(
        root=tmp_path,
        identity="alpha",
        document="# Alpha\n",
        support_files={"nested/data.bin": b"binary\x00"},
    )
    generated: Path = tmp_path / ".agents/skills/fensu-fixture/SKILL.md"
    generated.parent.mkdir(parents=True)
    original: str = generated_skill_text(root=tmp_path, body="old generated guidance\n")
    generated.write_text(original, encoding="utf-8")
    publisher: FailingSkillPublisher = FailingSkillPublisher(
        failure_at=test_case.failure_at,
        publish=installation._publish_staged_file,
    )
    monkeypatch.setattr(installation, "_publish_staged_file", publisher)
    monkeypatch.chdir(tmp_path)
    stderr: CaptureOutput = CaptureOutput()

    exit_code: int = run_skills(
        argv=("--target", "agents"),
        stderr=stderr,
    )

    assert exit_code == test_case.expected_exit_code
    assert test_case.expected_error_fragment in stderr.getvalue()
    assert generated.read_text(encoding="utf-8") == original
    assert not (tmp_path / ".agents/skills/alpha").exists()
