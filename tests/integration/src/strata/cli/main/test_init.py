"""Integration tests for repository-aware `strata init`."""

from __future__ import annotations

from pathlib import Path

import pytest

from strata.cli.main._init import run_init
from strata.config.main.load_config import load_config
from strata.config.models import Config
from strata.discovery.main.build_project_layout import build_project_layout
from strata.discovery.models import ProjectLayout, RepoRoot
from strata.reporting.constants import ANSI_BOLD_RED, ANSI_ORANGE
from strata.scaffolding._helpers.execution import build_rendered_config, render_config
from strata.scaffolding.constants import MEMORY_DIRECTORIES
from strata.scaffolding.models import InitPlan
from tests.integration.src.strata.cli.main._test_types import (
    InitApplicabilityTestCase,
    InitDriftWarningTestCase,
    InitExecutionTestCase,
    InitInteractiveTestCase,
    InitLocalTargetTestCase,
    InitMemoryTestCase,
    InitOptionTestCase,
    InitPresentationTestCase,
    InitPromptFailureTestCase,
    InitRefusalTestCase,
    InitRerunTestCase,
    InitRoundTripTestCase,
    InitSelectionTestCase,
    InitSymlinkRefusalTestCase,
    InitTranscriptTestCase,
)
from tests.integration.src.strata.cli.main.helpers import (
    TerminalBuffer,
    assert_init_execution_files,
    configure_no_color,
    configured_roots_or_none,
    existing_relative_paths,
    prepare_init_applicability_project,
    prepare_init_execution_project,
    prepare_init_refusal_project,
    prepare_init_transcript_project,
    prepare_unsafe_local_config_target,
    project_file_snapshot,
    write_broken_strata_symlink,
    write_init_editable_project,
    write_init_existing_config,
    write_init_hatch_project,
    write_init_invalid_python_project,
    write_init_invalid_utf8_project,
    write_selected_root_python_symlink,
)


@pytest.mark.parametrize(
    "test_case",
    [
        InitMemoryTestCase(
            description="explicit memory opt-in creates canonical empty structure and config",
            existing_memory_path=None,
            expected_exit_code=0,
            expected_enabled=True,
            expected_error_fragment="",
        )
    ],
    ids=lambda case: case.description,
)
def test_given_explicit_memory_option_when_initializing_then_creates_only_canonical_state(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    test_case: InitMemoryTestCase,
) -> None:
    configure_no_color(monkeypatch=monkeypatch, enabled=True)
    write_init_hatch_project(root=tmp_path, include_fault=False)
    stdout: TerminalBuffer = TerminalBuffer()
    stderr: TerminalBuffer = TerminalBuffer()

    exit_code: int = run_init(
        argv=("--yes", "--no-skills", "--memory"),
        stdin=TerminalBuffer(),
        stdout=stdout,
        stderr=stderr,
        working_directory=tmp_path,
    )

    assert exit_code == test_case.expected_exit_code
    assert test_case.expected_error_fragment in stderr.getvalue()
    assert (tmp_path / "strata.toml").is_file() is test_case.expected_enabled
    assert (
        all((tmp_path / path).is_dir() for path in MEMORY_DIRECTORIES) is test_case.expected_enabled
    )
    assert (tmp_path / ".strata/memory/memory.sqlite3").exists() is False
    config: Config = load_config(tmp_path)
    assert config.memory.enabled is test_case.expected_enabled
    assert config.memory.tasks.archive_after_days == 7
    assert ".strata/memory/" in (tmp_path / ".gitignore").read_text(encoding="utf-8")
    assert "Enabled repository memory in .ai/" in stdout.getvalue()


@pytest.mark.parametrize(
    "test_case",
    [
        InitMemoryTestCase(
            description="noncanonical existing memory refuses automatic migration before writes",
            existing_memory_path=".ai/legacy.md",
            expected_exit_code=2,
            expected_enabled=False,
            expected_error_fragment="will not be migrated automatically",
        )
    ],
    ids=lambda case: case.description,
)
def test_given_noncanonical_memory_when_initializing_then_refuses_before_writes(
    tmp_path: Path,
    test_case: InitMemoryTestCase,
) -> None:
    write_init_hatch_project(root=tmp_path, include_fault=False)
    existing: Path = tmp_path / str(test_case.existing_memory_path)
    existing.parent.mkdir(parents=True)
    existing.write_text("# Legacy\n", encoding="utf-8")
    stderr: TerminalBuffer = TerminalBuffer()

    exit_code: int = run_init(
        argv=("--yes", "--no-skills", "--memory"),
        stdin=TerminalBuffer(),
        stdout=TerminalBuffer(),
        stderr=stderr,
        working_directory=tmp_path,
    )

    assert exit_code == test_case.expected_exit_code
    assert test_case.expected_error_fragment in stderr.getvalue()
    assert (tmp_path / "strata.toml").is_file() is test_case.expected_enabled
    assert all((tmp_path / path).is_dir() for path in MEMORY_DIRECTORIES) is False
    assert existing.read_text(encoding="utf-8") == "# Legacy\n"
    assert not (tmp_path / ".gitignore").exists()


@pytest.mark.parametrize(
    "test_case",
    [
        InitInteractiveTestCase(
            description="Hatch package accepts detected layout without a tooling prompt",
            package_paths=("src/acme",),
            tooling_paths=(),
            scripted_input="\nn\n",
            expected_roots=("src/acme",),
            expected_tests=("tests",),
            expected_tooling=(),
            expected_output_fragments=(
                "src/acme      pyproject: hatch packages",
                "Accept? [Y/n/e]",
                "Install agent skill files?",
            ),
            expected_absent_fragments=("Tooling scope", "Use it?"),
        ),
        InitInteractiveTestCase(
            description="detected tooling is accepted separately from aggregate layout",
            package_paths=("src/acme",),
            tooling_paths=("scripts",),
            scripted_input="\ny\nn\n",
            expected_roots=("src/acme",),
            expected_tests=("tests",),
            expected_tooling=("scripts",),
            expected_output_fragments=(
                "Tooling scope",
                "Found scripts/ with Python files. Use it?",
            ),
        ),
        InitInteractiveTestCase(
            description="detected tooling can be declined separately",
            package_paths=("src/acme",),
            tooling_paths=("scripts",),
            scripted_input="\nn\nn\n",
            expected_roots=("src/acme",),
            expected_tests=("tests",),
            expected_tooling=(),
            expected_output_fragments=(
                "Tooling scope",
                "Run strata skills when you are ready.",
            ),
        ),
    ],
    ids=lambda case: case.description,
)
def test_given_detected_hatch_layout_when_answering_prompts_then_writes_selected_scopes(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    test_case: InitInteractiveTestCase,
) -> None:
    write_init_hatch_project(
        root=tmp_path,
        package_paths=test_case.package_paths,
        tooling_paths=test_case.tooling_paths,
    )
    stdin: TerminalBuffer = TerminalBuffer(test_case.scripted_input)
    stdout: TerminalBuffer = TerminalBuffer()
    stderr: TerminalBuffer = TerminalBuffer()
    configure_no_color(monkeypatch=monkeypatch, enabled=True)

    exit_code: int = run_init(
        argv=(), stdin=stdin, stdout=stdout, stderr=stderr, working_directory=tmp_path
    )
    config: Config = load_config(tmp_path)

    assert exit_code == 0
    assert config.roots == test_case.expected_roots
    assert config.tests == test_case.expected_tests
    assert config.tooling == test_case.expected_tooling
    assert all(fragment in stdout.getvalue() for fragment in test_case.expected_output_fragments)
    assert all(
        fragment not in stdout.getvalue() for fragment in test_case.expected_absent_fragments
    )
    assert stderr.getvalue() == ""


@pytest.mark.parametrize(
    "test_case",
    [
        InitExecutionTestCase(
            description="yes initializes existing faults with all rules and only summarizes drift",
            argv=("--yes", "--no-skills"),
            existing_project=True,
            stdin_isatty=False,
            stdout_isatty=False,
            expected_exit_code=0,
            expected_config=('roots = ["src/acme"]\ntests = ["tests"]\nselect = ["SF"]\n'),
            expected_output_fragments=(
                "Enabling the full Strata ruleset: SF",
                "SFA  annotations",
                "Found 1 fault across 1 file against the starting ruleset.",
            ),
            expected_absent_fragments=(
                "SFA101  module-level variables",
                " --> src/acme/constants.py",
            ),
        ),
        InitExecutionTestCase(
            description="named empty repository scaffolds exact files and full zero-drift config",
            argv=("--yes", "--name", "Sample-App", "--no-skills"),
            existing_project=False,
            stdin_isatty=False,
            stdout_isatty=False,
            expected_exit_code=0,
            expected_config=('roots = ["src/sample_app"]\ntests = ["tests"]\nselect = ["SF"]\n'),
            expected_output_fragments=(
                "Empty repository",
                "Created src/sample_app/__init__.py",
                "Created tests/",
                "Found 0 faults",
            ),
            expected_created_paths=(
                ".gitignore",
                "src/sample_app/__init__.py",
                "strata.toml",
                "tests/.gitkeep",
            ),
        ),
        InitExecutionTestCase(
            description="unanswered non-TTY initialization fails before prompts or writes",
            argv=(),
            existing_project=True,
            stdin_isatty=False,
            stdout_isatty=False,
            expected_exit_code=2,
            expected_config=None,
            expected_output_fragments=(),
            expected_error_fragment="Interactive initialization requires a TTY",
            expected_absent_fragments=("Detecting project layout", "Accept?"),
        ),
        InitExecutionTestCase(
            description="fully answered non-TTY initialization succeeds without yes",
            argv=("--root", "src/acme", "--tests", "tests", "--no-skills"),
            existing_project=True,
            stdin_isatty=False,
            stdout_isatty=False,
            expected_exit_code=0,
            expected_config=('roots = ["src/acme"]\ntests = ["tests"]\nselect = ["SF"]\n'),
            expected_output_fragments=("Wrote strata.toml",),
            expected_absent_fragments=("Accept?", "Project name"),
        ),
    ],
    ids=lambda case: case.description,
)
def test_given_repository_and_terminal_state_when_initializing_then_execution_is_atomic(
    tmp_path: Path,
    test_case: InitExecutionTestCase,
) -> None:
    before: tuple[str, ...] = prepare_init_execution_project(
        root=tmp_path, existing_project=test_case.existing_project
    )
    stdin: TerminalBuffer = TerminalBuffer(is_terminal=test_case.stdin_isatty)
    stdout: TerminalBuffer = TerminalBuffer(is_terminal=test_case.stdout_isatty)
    stderr: TerminalBuffer = TerminalBuffer(is_terminal=False)

    exit_code: int = run_init(
        argv=test_case.argv,
        stdin=stdin,
        stdout=stdout,
        stderr=stderr,
        working_directory=tmp_path,
    )

    assert exit_code == test_case.expected_exit_code
    assert all(fragment in stdout.getvalue() for fragment in test_case.expected_output_fragments)
    assert test_case.expected_error_fragment in stderr.getvalue()
    assert all(
        fragment not in stdout.getvalue() for fragment in test_case.expected_absent_fragments
    )
    assert_init_execution_files(
        root=tmp_path,
        before=before,
        expected_config=test_case.expected_config,
        expected_created_paths=test_case.expected_created_paths,
    )


@pytest.mark.parametrize(
    "test_case",
    [
        InitInteractiveTestCase(
            description="aggregate edit replaces roots and tests before writing",
            package_paths=("src/acme",),
            tooling_paths=(),
            scripted_input="e\nvendor/lib/other\nspecs\nn\n",
            expected_roots=("vendor/lib/other",),
            expected_tests=("specs",),
            expected_tooling=(),
            expected_output_fragments=("roots [src/acme]:", "tests [tests]:"),
        )
    ],
    ids=lambda case: case.description,
)
def test_given_detected_layout_when_editing_aggregate_then_validates_edited_roots_and_tests(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    test_case: InitInteractiveTestCase,
) -> None:
    write_init_editable_project(root=tmp_path)
    stdout: TerminalBuffer = TerminalBuffer()
    configure_no_color(monkeypatch=monkeypatch, enabled=True)

    exit_code: int = run_init(
        argv=(),
        stdin=TerminalBuffer(test_case.scripted_input),
        stdout=stdout,
        stderr=TerminalBuffer(),
        working_directory=tmp_path,
    )
    config: Config = load_config(tmp_path)

    assert exit_code == 0
    assert config.roots == test_case.expected_roots
    assert config.tests == test_case.expected_tests
    assert config.tooling == test_case.expected_tooling
    assert all(fragment in stdout.getvalue() for fragment in test_case.expected_output_fragments)


@pytest.mark.parametrize(
    "test_case",
    [
        InitInteractiveTestCase(
            description="explicit root is displayed as the layout being confirmed",
            package_paths=("src/acme",),
            tooling_paths=(),
            scripted_input="\n",
            expected_roots=("vendor/lib/other",),
            expected_tests=("tests",),
            expected_tooling=(),
            expected_output_fragments=(
                "    roots    vendor/lib/other command line",
                "    tests    tests/        directory scan",
                "    Accept? [Y/n/e]",
            ),
            expected_absent_fragments=("roots    src/acme",),
        )
    ],
    ids=lambda case: case.description,
)
def test_given_partial_explicit_root_when_confirming_layout_then_displays_command_line_root(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    test_case: InitInteractiveTestCase,
) -> None:
    write_init_editable_project(root=tmp_path)
    configure_no_color(monkeypatch=monkeypatch, enabled=True)
    stdout: TerminalBuffer = TerminalBuffer()

    exit_code: int = run_init(
        argv=("--root", *test_case.expected_roots, "--no-skills"),
        stdin=TerminalBuffer(test_case.scripted_input),
        stdout=stdout,
        stderr=TerminalBuffer(),
        working_directory=tmp_path,
    )
    config: Config = load_config(tmp_path)

    assert exit_code == 0
    assert config.roots == test_case.expected_roots
    assert config.tests == test_case.expected_tests
    assert all(fragment in stdout.getvalue() for fragment in test_case.expected_output_fragments)
    assert all(
        fragment not in stdout.getvalue() for fragment in test_case.expected_absent_fragments
    )


@pytest.mark.parametrize(
    "test_case",
    [
        InitSelectionTestCase(
            description="empty selection accepts all detected roots",
            scripted_input="\n\nn\n",
            expected_exit_code=0,
            expected_roots=("src/acme", "src/beta"),
            expected_output_fragments=("Found package roots:", "Include which?"),
        ),
        InitSelectionTestCase(
            description="numbered selection configures a root subset",
            scripted_input="2\n\nn\n",
            expected_exit_code=0,
            expected_roots=("src/beta",),
            expected_output_fragments=('Include which? [Enter = all, or e.g. "1,3"]',),
        ),
        InitSelectionTestCase(
            description="invalid selection retries and then accepts a valid subset",
            scripted_input="wat\n3\n1\n\nn\n",
            expected_exit_code=0,
            expected_roots=("src/acme",),
            expected_output_fragments=(
                "Invalid response 'wat'; try again.",
                "Invalid response '3'; try again.",
            ),
        ),
        InitSelectionTestCase(
            description="three invalid selections exhaust without writing",
            scripted_input="wat\n3\n1,1\n",
            expected_exit_code=2,
            expected_roots=None,
            expected_output_fragments=("Invalid response 'wat'; try again.",),
            expected_error_fragment="Invalid root selection after 3 attempts.",
        ),
    ],
    ids=lambda case: case.description,
)
def test_given_multiple_runtime_roots_when_selecting_then_defaults_retries_and_exhausts_safely(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    test_case: InitSelectionTestCase,
) -> None:
    write_init_hatch_project(root=tmp_path, package_paths=("src/acme", "src/beta"))
    stdout: TerminalBuffer = TerminalBuffer()
    stderr: TerminalBuffer = TerminalBuffer()
    configure_no_color(monkeypatch=monkeypatch, enabled=True)

    exit_code: int = run_init(
        argv=(),
        stdin=TerminalBuffer(test_case.scripted_input),
        stdout=stdout,
        stderr=stderr,
        working_directory=tmp_path,
    )

    assert exit_code == test_case.expected_exit_code
    assert all(fragment in stdout.getvalue() for fragment in test_case.expected_output_fragments)
    assert test_case.expected_error_fragment in stderr.getvalue()
    assert configured_roots_or_none(tmp_path) == test_case.expected_roots


@pytest.mark.parametrize(
    "test_case",
    [
        InitOptionTestCase(
            description="explicit scopes and skills install all defaults",
            argv=(
                "--yes",
                "--root",
                "src/acme",
                "src/beta",
                "--tests",
                "tests",
                "specs",
                "--tooling",
                "scripts",
                "--skills",
            ),
            expected_roots=("src/acme", "src/beta"),
            expected_tests=("tests", "specs"),
            expected_tooling=("scripts",),
            expected_select=("SF",),
            expected_skill_paths=(
                ".opencode/skills/strata-acme/SKILL.md",
                ".claude/skills/strata-acme/SKILL.md",
                ".agents/skills/strata-acme/SKILL.md",
            ),
        ),
        InitOptionTestCase(
            description="explicit scopes and no-skills preserve detected tooling",
            argv=(
                "--yes",
                "--root",
                "src/acme",
                "--tests",
                "tests",
                "--no-skills",
            ),
            expected_roots=("src/acme",),
            expected_tests=("tests",),
            expected_tooling=("scripts",),
            expected_select=("SF",),
            expected_skill_paths=(),
        ),
    ],
    ids=lambda case: case.description,
)
def test_given_explicit_scope_adoption_and_skill_options_when_initializing_then_honors_all_flags(
    tmp_path: Path,
    test_case: InitOptionTestCase,
) -> None:
    write_init_hatch_project(
        root=tmp_path,
        package_paths=("src/acme", "src/beta"),
        tooling_paths=("scripts",),
    )
    (tmp_path / "specs").mkdir()
    stdout: TerminalBuffer = TerminalBuffer(is_terminal=False)

    exit_code: int = run_init(
        argv=test_case.argv,
        stdin=TerminalBuffer(is_terminal=False),
        stdout=stdout,
        stderr=TerminalBuffer(is_terminal=False),
        working_directory=tmp_path,
        home_dir=tmp_path / "home",
    )
    config: Config = load_config(tmp_path)

    assert exit_code == 0
    assert config.roots == test_case.expected_roots
    assert config.tests == test_case.expected_tests
    assert config.tooling == test_case.expected_tooling
    assert config.select == test_case.expected_select
    assert (
        existing_relative_paths(root=tmp_path, paths=test_case.expected_skill_paths)
        == test_case.expected_skill_paths
    )
    assert ("Run strata skills" in stdout.getvalue()) is (not test_case.expected_skill_paths)


@pytest.mark.parametrize(
    "test_case",
    [
        InitRefusalTestCase(
            description="aggregate decline refuses without writing",
            source="decline",
            scripted_input="n\n",
            expected_error_fragment="Initialization declined; no files were written.",
        ),
        InitRefusalTestCase(
            description="parent config is refused without a child write",
            source="parent",
            scripted_input="",
            expected_error_fragment="Strata configuration already exists:",
        ),
    ],
    ids=lambda case: case.description,
)
def test_given_decline_or_existing_configuration_when_initializing_then_refuses_without_write(
    tmp_path: Path,
    test_case: InitRefusalTestCase,
) -> None:
    repository, before = prepare_init_refusal_project(root=tmp_path, source=test_case.source)
    stdout: TerminalBuffer = TerminalBuffer()
    stderr: TerminalBuffer = TerminalBuffer()

    exit_code: int = run_init(
        argv=test_case.argv,
        stdin=TerminalBuffer(test_case.scripted_input),
        stdout=stdout,
        stderr=stderr,
        working_directory=repository,
    )

    assert exit_code == test_case.expected_exit_code
    assert test_case.expected_error_fragment in stderr.getvalue()
    assert test_case.expected_stdout_fragment in stdout.getvalue()
    assert project_file_snapshot(repository) == before
    assert (repository / "strata.toml").exists() is (test_case.source == "strata.toml")


@pytest.mark.parametrize(
    "test_case",
    [
        InitRerunTestCase(
            description="local strata toml ignores valid different init flags",
            source="strata.toml",
            argv=("--name", "ignored"),
            expected_relative_config="strata.toml",
            expected_exit_code=0,
        ),
        InitRerunTestCase(
            description="local tool strata table ignores different init flags",
            source="tool.strata",
            argv=("--yes", "--root", "ignored", "--skills"),
            expected_relative_config="pyproject.toml",
            expected_exit_code=0,
        ),
    ],
    ids=lambda case: case.description,
)
def test_given_local_configuration_when_rerunning_init_then_succeeds_before_options_or_tty(
    tmp_path: Path,
    test_case: InitRerunTestCase,
) -> None:
    write_init_hatch_project(root=tmp_path)
    _ = write_init_existing_config(root=tmp_path, source=test_case.source)
    before: tuple[str, ...] = project_file_snapshot(tmp_path)
    stdout: TerminalBuffer = TerminalBuffer(is_terminal=False)
    stderr: TerminalBuffer = TerminalBuffer(is_terminal=False)

    exit_code: int = run_init(
        argv=test_case.argv,
        stdin=TerminalBuffer(is_terminal=False),
        stdout=stdout,
        stderr=stderr,
        working_directory=tmp_path,
    )

    expected_path: Path = tmp_path / test_case.expected_relative_config
    assert exit_code == test_case.expected_exit_code
    assert stdout.getvalue() == (
        f"Strata configuration already exists: {expected_path} (nothing to do)\n"
    )
    assert stderr.getvalue() == ""
    assert project_file_snapshot(tmp_path) == before


@pytest.mark.parametrize(
    "test_case",
    [
        InitExecutionTestCase(
            description="interactive skill decline prints the later command and writes no skills",
            argv=(),
            existing_project=True,
            stdin_isatty=True,
            stdout_isatty=True,
            expected_exit_code=0,
            expected_config=None,
            expected_output_fragments=("Run strata skills when you are ready.",),
        )
    ],
    ids=lambda case: case.description,
)
def test_given_skill_prompt_when_declining_then_preserves_config_and_prints_update_command(
    tmp_path: Path,
    test_case: InitExecutionTestCase,
) -> None:
    write_init_hatch_project(root=tmp_path)
    stdout: TerminalBuffer = TerminalBuffer()

    exit_code: int = run_init(
        argv=test_case.argv,
        stdin=TerminalBuffer("\nn\n"),
        stdout=stdout,
        stderr=TerminalBuffer(),
        working_directory=tmp_path,
    )

    assert exit_code == test_case.expected_exit_code
    assert all(fragment in stdout.getvalue() for fragment in test_case.expected_output_fragments)
    assert (tmp_path / "strata.toml").is_file()
    assert not (tmp_path / ".opencode").exists()


@pytest.mark.parametrize(
    "test_case",
    [
        InitExecutionTestCase(
            description="default yes installs real skill files and reports repository paths",
            argv=("--yes",),
            existing_project=True,
            stdin_isatty=False,
            stdout_isatty=False,
            expected_exit_code=0,
            expected_config=None,
            expected_output_fragments=(
                "Updated .opencode/skills/strata-acme/SKILL.md",
                "Updated .claude/skills/strata-acme/SKILL.md",
                "Updated .agents/skills/strata-acme/SKILL.md",
            ),
            expected_created_paths=(
                ".agents/skills/strata-acme/SKILL.md",
                ".claude/skills/strata-acme/SKILL.md",
                ".opencode/skills/strata-acme/SKILL.md",
            ),
        )
    ],
    ids=lambda case: case.description,
)
def test_given_yes_with_default_skills_when_initializing_then_installs_real_repository_targets(
    tmp_path: Path,
    test_case: InitExecutionTestCase,
) -> None:
    write_init_hatch_project(root=tmp_path)
    stdout: TerminalBuffer = TerminalBuffer(is_terminal=False)

    exit_code: int = run_init(
        argv=test_case.argv,
        stdin=TerminalBuffer(is_terminal=False),
        stdout=stdout,
        stderr=TerminalBuffer(is_terminal=False),
        working_directory=tmp_path,
        home_dir=tmp_path / "home",
    )

    assert exit_code == test_case.expected_exit_code
    assert all(fragment in stdout.getvalue() for fragment in test_case.expected_output_fragments)
    assert all((tmp_path / path).is_file() for path in test_case.expected_created_paths)


@pytest.mark.parametrize(
    "test_case",
    [
        InitExecutionTestCase(
            description="monorepo init installs discoverable project skill at parent Git root",
            argv=("--yes",),
            existing_project=True,
            stdin_isatty=False,
            stdout_isatty=False,
            expected_exit_code=0,
            expected_config=None,
            expected_output_fragments=(
                "Updated ../.opencode/skills/strata-acme/SKILL.md",
                "Updated ../.claude/skills/strata-acme/SKILL.md",
                "Updated ../.agents/skills/strata-acme/SKILL.md",
            ),
            expected_created_paths=(
                ".agents/skills/strata-acme/SKILL.md",
                ".claude/skills/strata-acme/SKILL.md",
                ".opencode/skills/strata-acme/SKILL.md",
            ),
        )
    ],
    ids=lambda case: case.description,
)
def test_given_monorepo_project_when_initializing_then_installs_at_git_root_with_prefixed_paths(
    tmp_path: Path,
    test_case: InitExecutionTestCase,
) -> None:
    (tmp_path / ".git").mkdir()
    project: Path = tmp_path / "backend"
    project.mkdir()
    write_init_hatch_project(root=project)
    stdout: TerminalBuffer = TerminalBuffer(is_terminal=False)

    exit_code: int = run_init(
        argv=test_case.argv,
        stdin=TerminalBuffer(is_terminal=False),
        stdout=stdout,
        stderr=TerminalBuffer(is_terminal=False),
        working_directory=project,
        home_dir=tmp_path / "home",
    )
    content: str = (tmp_path / test_case.expected_created_paths[0]).read_text(encoding="utf-8")

    assert exit_code == test_case.expected_exit_code
    assert all(fragment in stdout.getvalue() for fragment in test_case.expected_output_fragments)
    assert all((tmp_path / path).is_file() for path in test_case.expected_created_paths)
    assert 'Configuration source: "backend/strata.toml"' in content
    assert '- Product roots: ["backend/src/acme"]' in content


@pytest.mark.parametrize(
    "test_case",
    [
        InitExecutionTestCase(
            description="later skill target failure preflights atomically and preserves config",
            argv=("--yes",),
            existing_project=True,
            stdin_isatty=False,
            stdout_isatty=False,
            expected_exit_code=0,
            expected_config=None,
            expected_output_fragments=("Next",),
            expected_error_fragment="Could not update agent skill files:",
        )
    ],
    ids=lambda case: case.description,
)
def test_given_unwritable_skill_target_when_initializing_then_preserves_written_config(
    tmp_path: Path,
    test_case: InitExecutionTestCase,
) -> None:
    write_init_hatch_project(root=tmp_path)
    (tmp_path / ".agents").write_text("blocking later target\n", encoding="utf-8")
    stdout: TerminalBuffer = TerminalBuffer(is_terminal=False)
    stderr: TerminalBuffer = TerminalBuffer(is_terminal=False)

    exit_code: int = run_init(
        argv=test_case.argv,
        stdin=TerminalBuffer(is_terminal=False),
        stdout=stdout,
        stderr=stderr,
        working_directory=tmp_path,
        home_dir=tmp_path / "home",
    )
    config: Config = load_config(tmp_path)

    assert exit_code == test_case.expected_exit_code
    assert all(fragment in stdout.getvalue() for fragment in test_case.expected_output_fragments)
    assert test_case.expected_error_fragment in stderr.getvalue()
    assert config.roots == ("src/acme",)
    assert (tmp_path / "strata.toml").is_file()
    assert not (tmp_path / ".opencode").exists()
    assert not (tmp_path / ".claude").exists()


@pytest.mark.parametrize(
    "test_case",
    [
        InitPresentationTestCase(
            description="plain stream has semantic transcript without ANSI",
            is_terminal=False,
            no_color=False,
            include_fault=True,
            expected_output_fragments=(
                "--> Detecting project layout",
                "SFA  annotations",
                "Found 1 fault",
            ),
            expected_absent_fragments=("\033[",),
        ),
        InitPresentationTestCase(
            description="colored stream uses orange only for drift fault contexts",
            is_terminal=True,
            no_color=False,
            include_fault=True,
            expected_output_fragments=(
                "\033[1;36m-->\033[0m \033[1mDetecting project layout\033[0m",
                "\033[1mtests/\033[0m",
                "\033[2mnone detected\033[0m",
                f"{ANSI_ORANGE}SFA\033[0m",
                f"{ANSI_BOLD_RED}1 fault\033[0m",
            ),
            expected_absent_fragments=(f"{ANSI_ORANGE}Detecting", f"{ANSI_ORANGE}strata.toml"),
        ),
        InitPresentationTestCase(
            description="NO_COLOR disables ANSI on a terminal",
            is_terminal=True,
            no_color=True,
            include_fault=True,
            expected_output_fragments=("--> Detecting project layout", "SFA  annotations"),
            expected_absent_fragments=("\033[",),
        ),
        InitPresentationTestCase(
            description="zero drift success contains no orange context",
            is_terminal=True,
            no_color=False,
            include_fault=False,
            expected_output_fragments=("\033[1;32mFound 0 faults\033[0m",),
            expected_absent_fragments=(ANSI_ORANGE, ANSI_BOLD_RED),
        ),
    ],
    ids=lambda case: case.description,
)
def test_given_terminal_color_controls_when_initializing_then_applies_semantic_theme_only(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    test_case: InitPresentationTestCase,
) -> None:
    write_init_hatch_project(root=tmp_path, include_fault=test_case.include_fault)
    configure_no_color(monkeypatch=monkeypatch, enabled=test_case.no_color)
    stdout: TerminalBuffer = TerminalBuffer(is_terminal=test_case.is_terminal)

    exit_code: int = run_init(
        argv=("--yes", "--no-skills"),
        stdin=TerminalBuffer(is_terminal=False),
        stdout=stdout,
        stderr=TerminalBuffer(is_terminal=False),
        working_directory=tmp_path,
    )

    assert exit_code == 0
    assert all(fragment in stdout.getvalue() for fragment in test_case.expected_output_fragments)
    assert all(
        fragment not in stdout.getvalue() for fragment in test_case.expected_absent_fragments
    )


@pytest.mark.parametrize(
    "test_case",
    [
        InitDriftWarningTestCase(
            description="invalid Python warns after config write and continues skill decision and Next",
            scripted_input="\nn\n",
            expected_exit_code=0,
            expected_output_fragments=(
                "Wrote strata.toml",
                "Install agent skill files? [Y/n]",
                "Run strata skills when you are ready.",
                "--> Next",
            ),
            expected_warning_fragment="Warning: could not measure current drift: Could not parse",
        )
    ],
    ids=lambda case: case.description,
)
def test_given_invalid_python_after_write_when_measuring_drift_then_warns_and_continues(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    test_case: InitDriftWarningTestCase,
) -> None:
    write_init_invalid_python_project(root=tmp_path)
    configure_no_color(monkeypatch=monkeypatch, enabled=True)
    stdout: TerminalBuffer = TerminalBuffer()
    stderr: TerminalBuffer = TerminalBuffer()

    exit_code: int = run_init(
        argv=(),
        stdin=TerminalBuffer(test_case.scripted_input),
        stdout=stdout,
        stderr=stderr,
        working_directory=tmp_path,
    )
    config: Config = load_config(tmp_path)

    assert exit_code == test_case.expected_exit_code
    assert all(fragment in stdout.getvalue() for fragment in test_case.expected_output_fragments)
    assert test_case.expected_warning_fragment in stderr.getvalue()
    assert config.roots == ("src/acme",)
    assert (tmp_path / "strata.toml").is_file()


@pytest.mark.parametrize(
    "test_case",
    [
        InitDriftWarningTestCase(
            description="invalid UTF-8 warns after config write and continues skill decision and Next",
            scripted_input="\nn\n",
            expected_exit_code=0,
            expected_output_fragments=(
                "Wrote strata.toml",
                "Install agent skill files? [Y/n]",
                "Run strata skills when you are ready.",
                "--> Next",
            ),
            expected_warning_fragment="Warning: could not measure current drift:",
        )
    ],
    ids=lambda case: case.description,
)
def test_given_invalid_utf8_python_when_measuring_drift_then_warns_and_continues(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    test_case: InitDriftWarningTestCase,
) -> None:
    write_init_invalid_utf8_project(root=tmp_path)
    configure_no_color(monkeypatch=monkeypatch, enabled=True)
    stdout: TerminalBuffer = TerminalBuffer()
    stderr: TerminalBuffer = TerminalBuffer()

    exit_code: int = run_init(
        argv=(),
        stdin=TerminalBuffer(test_case.scripted_input),
        stdout=stdout,
        stderr=stderr,
        working_directory=tmp_path,
    )
    config: Config = load_config(tmp_path)

    assert exit_code == test_case.expected_exit_code
    assert all(fragment in stdout.getvalue() for fragment in test_case.expected_output_fragments)
    assert test_case.expected_warning_fragment in stderr.getvalue()
    assert "Traceback" not in f"{stdout.getvalue()}{stderr.getvalue()}"
    assert config.roots == ("src/acme",)
    assert (tmp_path / "strata.toml").is_file()


@pytest.mark.parametrize(
    "test_case",
    [
        InitApplicabilityTestCase(
            description="name is rejected for an existing Python project",
            existing_project=True,
            argv=("--yes", "--name", "other", "--no-skills"),
            expected_error_fragment="--name only applies when no Python package is detected.",
            expected_error="--name only applies when no Python package is detected.\n",
        ),
        InitApplicabilityTestCase(
            description="yes requires an explicit name for an empty scaffold",
            existing_project=False,
            argv=("--yes", "--no-skills"),
            expected_error_fragment=(
                "Empty repository initialization with --yes requires --name NAME."
            ),
            expected_error=(
                "Empty repository initialization with --yes requires --name NAME.\n"
                "Example: strata init --yes --name my_package\n"
            ),
        ),
        InitApplicabilityTestCase(
            description="root is rejected for an empty scaffold",
            existing_project=False,
            argv=("--yes", "--root", "src/acme", "--no-skills"),
            expected_error_fragment="Explicit --root, --tests, and --tooling options do not apply",
            expected_error=(
                "Explicit --root, --tests, and --tooling options do not apply to an empty "
                "scaffold; use --name to choose its package.\n"
            ),
        ),
        InitApplicabilityTestCase(
            description="tests are rejected for an empty scaffold",
            existing_project=False,
            argv=("--yes", "--tests", "tests", "--no-skills"),
            expected_error_fragment="Explicit --root, --tests, and --tooling options do not apply",
            expected_error=(
                "Explicit --root, --tests, and --tooling options do not apply to an empty "
                "scaffold; use --name to choose its package.\n"
            ),
        ),
        InitApplicabilityTestCase(
            description="tooling is rejected for an empty scaffold",
            existing_project=False,
            argv=("--yes", "--tooling", "scripts", "--no-skills"),
            expected_error_fragment="Explicit --root, --tests, and --tooling options do not apply",
            expected_error=(
                "Explicit --root, --tests, and --tooling options do not apply to an empty "
                "scaffold; use --name to choose its package.\n"
            ),
        ),
    ],
    ids=lambda case: case.description,
)
def test_given_inapplicable_options_when_initializing_then_rejects_before_output_or_write(
    tmp_path: Path,
    test_case: InitApplicabilityTestCase,
) -> None:
    before: tuple[str, ...] = prepare_init_applicability_project(
        root=tmp_path, existing_project=test_case.existing_project
    )
    stdout: TerminalBuffer = TerminalBuffer(is_terminal=False)
    stderr: TerminalBuffer = TerminalBuffer(is_terminal=False)

    exit_code: int = run_init(
        argv=test_case.argv,
        stdin=TerminalBuffer(is_terminal=False),
        stdout=stdout,
        stderr=stderr,
        working_directory=tmp_path,
    )

    assert exit_code == 2
    assert test_case.expected_error_fragment in stderr.getvalue()
    assert stderr.getvalue() == test_case.expected_error
    assert stdout.getvalue() == ""
    assert project_file_snapshot(tmp_path) == before
    assert not (tmp_path / "strata.toml").exists()


@pytest.mark.parametrize(
    "test_case",
    [
        InitSymlinkRefusalTestCase(
            description="broken local strata config symlink is refused without touching outside target",
            expected_exit_code=2,
            expected_error_fragment="Strata configuration path is a symlink:",
            expected_stdout="",
        )
    ],
    ids=lambda case: case.description,
)
def test_given_broken_local_config_symlink_when_initializing_then_refuses_without_outside_write(
    tmp_path: Path,
    test_case: InitSymlinkRefusalTestCase,
) -> None:
    outside_target: Path = tmp_path.parent / f"{tmp_path.name}-outside.toml"
    write_init_hatch_project(root=tmp_path)
    write_broken_strata_symlink(root=tmp_path, outside_target=outside_target)
    stdout: TerminalBuffer = TerminalBuffer(is_terminal=False)
    stderr: TerminalBuffer = TerminalBuffer(is_terminal=False)

    exit_code: int = run_init(
        argv=("--yes",),
        stdin=TerminalBuffer(is_terminal=False),
        stdout=stdout,
        stderr=stderr,
        working_directory=tmp_path,
    )

    assert exit_code == test_case.expected_exit_code
    assert test_case.expected_error_fragment in stderr.getvalue()
    assert stdout.getvalue() == test_case.expected_stdout
    assert (tmp_path / "strata.toml").is_symlink()
    assert not outside_target.exists()


@pytest.mark.parametrize(
    "test_case",
    [
        InitLocalTargetTestCase(
            description="local strata config directory is refused",
            target_kind="strata-directory",
            expected_error_fragment="Strata configuration path is not a regular file:",
            expected_exit_code=2,
        ),
        InitLocalTargetTestCase(
            description="local pyproject symlink is refused",
            target_kind="pyproject-symlink",
            expected_error_fragment="Pyproject configuration path is a symlink:",
            expected_exit_code=2,
        ),
        InitLocalTargetTestCase(
            description="local pyproject directory is refused",
            target_kind="pyproject-directory",
            expected_error_fragment="Pyproject configuration path is not a regular file:",
            expected_exit_code=2,
        ),
    ],
    ids=lambda case: case.description,
)
def test_given_unsafe_local_config_target_when_initializing_then_refuses_without_publication(
    tmp_path: Path,
    test_case: InitLocalTargetTestCase,
) -> None:
    target: Path = prepare_unsafe_local_config_target(
        root=tmp_path, target_kind=test_case.target_kind
    )
    stdout: TerminalBuffer = TerminalBuffer(is_terminal=False)
    stderr: TerminalBuffer = TerminalBuffer(is_terminal=False)

    exit_code: int = run_init(
        argv=("--yes", "--no-skills"),
        stdin=TerminalBuffer(is_terminal=False),
        stdout=stdout,
        stderr=stderr,
        working_directory=tmp_path,
    )

    assert exit_code == test_case.expected_exit_code
    assert test_case.expected_error_fragment in stderr.getvalue()
    assert stdout.getvalue() == ""
    assert target.exists() or target.is_symlink()
    assert not (tmp_path / ".gitignore").exists()
    assert not (tmp_path / "strata.toml").is_file()


@pytest.mark.parametrize(
    "test_case",
    [
        InitTranscriptTestCase(
            description="existing interactive flow has the complete canonical plain transcript",
            existing_project=True,
            argv=(),
            scripted_input="\nn\n",
            expected_transcript=(
                "--> Detecting project layout\n"
                "\n"
                "    roots    src/acme      pyproject: hatch packages\n"
                "    tests    tests/        directory scan\n"
                "    tooling  none detected\n"
                "\n"
                "    Accept? [Y/n/e] e = edit paths \n"
                "\n"
                "--> Existing codebase - 1 Python file\n"
                "\n"
                "    Enabling the full Strata ruleset: SF\n"
                "    Wrote strata.toml\n"
                "\n"
                "--> Measuring current drift\n"
                "\n"
                "    SFA  annotations       1\n"
                "    SFL  layers            0\n"
                "    SFH  hygiene           0\n"
                "    SFN  naming            0\n"
                "    SFR  roles             2\n"
                "    SFS  shape             0\n"
                "    SFT  tests             0\n"
                "\n"
                "    Found 3 faults across 1 file against the starting ruleset.\n"
                "    See docs.stratalint.com/adoption for rolling out gradually.\n"
                "\n"
                "--> Install agent skill files? [Y/n] \n"
                "\n"
                "    Run strata skills when you are ready.\n"
                "\n"
                "--> Next\n"
                "\n"
                "    strata check            run anytime\n"
                "    strata rule SFA001      inspect any code in the output\n"
            ),
        ),
        InitTranscriptTestCase(
            description="empty yes flow has the complete canonical plain transcript",
            existing_project=False,
            argv=("--yes", "--name", "Sample-App", "--no-skills"),
            scripted_input="",
            expected_transcript=(
                "--> Empty repository\n"
                "\n"
                "    Created src/sample_app/__init__.py\n"
                "    Created tests/\n"
                "    Wrote strata.toml\n"
                "\n"
                "--> Found 0 faults\n"
                "\n"
                "--> Agent skill files - no\n"
                "\n"
                "    Run strata skills when you are ready.\n"
                "\n"
                "--> Next\n"
                "\n"
                "    strata check            run anytime\n"
                "    strata rule SFA001      inspect any code in the output\n"
            ),
        ),
    ],
    ids=lambda case: case.description,
)
def test_given_representative_plain_flow_when_initializing_then_emits_exact_canonical_transcript(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    test_case: InitTranscriptTestCase,
) -> None:
    prepare_init_transcript_project(root=tmp_path, existing_project=test_case.existing_project)
    configure_no_color(monkeypatch=monkeypatch, enabled=True)
    stdout: TerminalBuffer = TerminalBuffer(is_terminal=test_case.existing_project)
    stderr: TerminalBuffer = TerminalBuffer(is_terminal=False)

    exit_code: int = run_init(
        argv=test_case.argv,
        stdin=TerminalBuffer(test_case.scripted_input, is_terminal=test_case.existing_project),
        stdout=stdout,
        stderr=stderr,
        working_directory=tmp_path,
    )

    assert exit_code == 0
    assert stdout.getvalue() == test_case.expected_transcript
    assert stderr.getvalue() == ""


@pytest.mark.parametrize(
    "test_case",
    [
        InitPromptFailureTestCase(
            description="EOF while reading the first prompt exits without writing config",
            scripted_input="",
            expected_exit_code=2,
            expected_error_fragment=(
                "Unexpected EOF while reading layout confirmation; offending raw value: <EOF>."
            ),
            expected_config_written=False,
            expected_output_fragment="Accept? [Y/n/e]",
        )
    ],
    ids=lambda case: case.description,
)
def test_given_eof_before_first_prompt_response_when_initializing_then_exits_without_write(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    test_case: InitPromptFailureTestCase,
) -> None:
    write_init_hatch_project(root=tmp_path)
    before: tuple[str, ...] = project_file_snapshot(tmp_path)
    configure_no_color(monkeypatch=monkeypatch, enabled=True)
    stdout: TerminalBuffer = TerminalBuffer()
    stderr: TerminalBuffer = TerminalBuffer()

    exit_code: int = run_init(
        argv=(),
        stdin=TerminalBuffer(test_case.scripted_input),
        stdout=stdout,
        stderr=stderr,
        working_directory=tmp_path,
    )

    assert exit_code == test_case.expected_exit_code
    assert test_case.expected_error_fragment in stderr.getvalue()
    assert test_case.expected_output_fragment in stdout.getvalue()
    assert test_case.expected_absent_fragment not in f"{stdout.getvalue()}{stderr.getvalue()}"
    assert (tmp_path / "strata.toml").exists() is test_case.expected_config_written
    assert project_file_snapshot(tmp_path) == before


@pytest.mark.parametrize(
    "test_case",
    [
        InitPromptFailureTestCase(
            description="EOF at the post-write skill prompt exits cleanly with valid config",
            scripted_input="\n",
            expected_exit_code=2,
            expected_error_fragment=(
                "Unexpected EOF while reading yes/no confirmation; offending raw value: <EOF>."
            ),
            expected_config_written=True,
            expected_output_fragment="Install agent skill files? [Y/n]",
        ),
        InitPromptFailureTestCase(
            description="three invalid skill responses exit cleanly with valid config",
            scripted_input="\nwat\nmaybe\nlater\n",
            expected_exit_code=2,
            expected_error_fragment=(
                "Invalid response after 3 attempts; expected y/n. Final raw value: 'later'."
            ),
            expected_config_written=True,
            expected_output_fragment="Invalid response 'maybe'; try again.",
        ),
    ],
    ids=lambda case: case.description,
)
def test_given_failed_final_skill_prompt_when_initializing_then_preserves_valid_config(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    test_case: InitPromptFailureTestCase,
) -> None:
    write_init_hatch_project(root=tmp_path)
    configure_no_color(monkeypatch=monkeypatch, enabled=True)
    stdout: TerminalBuffer = TerminalBuffer()
    stderr: TerminalBuffer = TerminalBuffer()

    exit_code: int = run_init(
        argv=(),
        stdin=TerminalBuffer(test_case.scripted_input),
        stdout=stdout,
        stderr=stderr,
        working_directory=tmp_path,
    )
    config: Config = load_config(tmp_path)

    assert exit_code == test_case.expected_exit_code
    assert test_case.expected_error_fragment in stderr.getvalue()
    assert test_case.expected_output_fragment in stdout.getvalue()
    assert test_case.expected_absent_fragment not in f"{stdout.getvalue()}{stderr.getvalue()}"
    assert (tmp_path / "strata.toml").exists() is test_case.expected_config_written
    assert config.roots == ("src/acme",)
    assert "--> Next" not in stdout.getvalue()


@pytest.mark.parametrize(
    "test_case",
    [
        InitSymlinkRefusalTestCase(
            description="selected runtime Python symlink is refused before config write",
            expected_exit_code=2,
            expected_error_fragment="Selected scope contains a symlinked Python path:",
            expected_stdout="Detecting project layout",
        )
    ],
    ids=lambda case: case.description,
)
def test_given_selected_root_python_symlink_when_initializing_then_refuses_before_write(
    tmp_path: Path,
    test_case: InitSymlinkRefusalTestCase,
) -> None:
    outside_target: Path = tmp_path.parent / f"{tmp_path.name}-outside.py"
    write_init_hatch_project(root=tmp_path)
    write_selected_root_python_symlink(root=tmp_path, outside_target=outside_target)
    outside_content: str = outside_target.read_text(encoding="utf-8")
    stdout: TerminalBuffer = TerminalBuffer(is_terminal=False)
    stderr: TerminalBuffer = TerminalBuffer(is_terminal=False)

    exit_code: int = run_init(
        argv=("--yes", "--no-skills"),
        stdin=TerminalBuffer(is_terminal=False),
        stdout=stdout,
        stderr=stderr,
        working_directory=tmp_path,
    )

    assert exit_code == test_case.expected_exit_code
    assert test_case.expected_error_fragment in stderr.getvalue()
    assert test_case.expected_stdout in stdout.getvalue()
    assert "Traceback" not in f"{stdout.getvalue()}{stderr.getvalue()}"
    assert not (tmp_path / "strata.toml").exists()
    assert outside_target.read_text(encoding="utf-8") == outside_content


@pytest.mark.parametrize(
    "test_case",
    [
        InitRoundTripTestCase(
            description="rendered config round-trips into the authoritative project layout",
            expected_roots=("src/acme", "src/beta"),
            expected_tests=("tests", "specs"),
            expected_tooling=("scripts",),
            expected_select=("SF",),
        )
    ],
    ids=lambda case: case.description,
)
def test_given_init_plan_when_rendering_and_building_layout_then_round_trips_validated_config(
    tmp_path: Path,
    test_case: InitRoundTripTestCase,
) -> None:
    write_init_hatch_project(
        root=tmp_path,
        package_paths=test_case.expected_roots,
        tooling_paths=test_case.expected_tooling,
    )
    (tmp_path / "specs").mkdir()
    plan: InitPlan = InitPlan(
        roots=test_case.expected_roots,
        tests=test_case.expected_tests,
        tooling=test_case.expected_tooling,
    )

    config: Config = build_rendered_config(text=render_config(plan=plan))
    layout: ProjectLayout = build_project_layout(
        config=config, repo_root=RepoRoot(path=tmp_path.resolve())
    )

    assert config.roots == test_case.expected_roots
    assert config.tests == test_case.expected_tests
    assert config.tooling == test_case.expected_tooling
    assert config.select == test_case.expected_select
    assert (
        tuple(source.path.relative_to(tmp_path).as_posix() for source in layout.runtime_sources)
        == test_case.expected_roots
    )
    assert (
        tuple(root.path.relative_to(tmp_path).as_posix() for root in layout.test_roots)
        == test_case.expected_tests
    )
    assert (
        tuple(source.path.relative_to(tmp_path).as_posix() for source in layout.tooling_sources)
        == test_case.expected_tooling
    )
