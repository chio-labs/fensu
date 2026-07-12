"""Installed-console end-to-end tests for repository initialization."""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from strata.scaffolding.constants import PYTHON_GITIGNORE_TEMPLATE, STRATA_GITIGNORE_BLOCK
from tests.e2e.src.strata.cli.main._test_types import (
    CliProjectFile,
    InstalledInitCliTestCase,
)
from tests.e2e.src.strata.cli.main.helpers import (
    config_values,
    repository_text_snapshot,
    run_cli_init,
    write_project_files,
)


@pytest.mark.parametrize(
    "test_case",
    [
        InstalledInitCliTestCase(
            description="existing Hatch package writes gradual config despite drift",
            argv=("--yes", "--no-skills"),
            input_text="",
            initial_files=(
                CliProjectFile(
                    relative_path="pyproject.toml",
                    source=(
                        '[project]\nname = "tiny"\n\n'
                        "[tool.hatch.build.targets.wheel]\n"
                        'packages = ["src/tiny"]\n'
                    ),
                ),
                CliProjectFile(relative_path="src/tiny/__init__.py", source="VALUE = 1\n"),
            ),
            expected_exit_code=0,
            expected_files=(
                CliProjectFile(
                    relative_path=".gitignore",
                    source=STRATA_GITIGNORE_BLOCK.decode(),
                ),
                CliProjectFile(
                    relative_path="pyproject.toml",
                    source=(
                        '[project]\nname = "tiny"\n\n'
                        "[tool.hatch.build.targets.wheel]\n"
                        'packages = ["src/tiny"]\n'
                    ),
                ),
                CliProjectFile(
                    relative_path="src/tiny/__init__.py",
                    source="VALUE = 1\n",
                ),
                CliProjectFile(
                    relative_path="strata.toml",
                    source=(
                        'roots = ["src/tiny"]\n'
                        'tests = ["tests"]\n'
                        "# Adoption guide: https://docs.stratalint.com/adoption\n"
                        'select = ["SFL", "SFX", "SFA", "SFN"]\n'
                    ),
                ),
            ),
            expected_config_values=(
                ("roots", ("src/tiny",)),
                ("tests", ("tests",)),
                ("select", ("SFL", "SFX", "SFA", "SFN")),
            ),
            expected_stdout_fragments=(
                "Existing codebase - 1 Python file",
                "Starting with the gradual ruleset",
                "Measuring current drift",
                "Found 1 fault across 1 file",
                "Wrote strata.toml",
            ),
            expected_stderr_fragments=(),
            expected_absent_output_fragments=("\x1b[",),
            expected_stdout_is_empty=False,
        ),
        InstalledInitCliTestCase(
            description="empty repository scaffolds named full project",
            argv=("--yes", "--name", "my-project", "--no-skills"),
            input_text="",
            initial_files=(),
            expected_exit_code=0,
            expected_files=(
                CliProjectFile(
                    relative_path=".gitignore",
                    source=(PYTHON_GITIGNORE_TEMPLATE + STRATA_GITIGNORE_BLOCK).decode(),
                ),
                CliProjectFile(relative_path="src/my_project/__init__.py", source=""),
                CliProjectFile(
                    relative_path="strata.toml",
                    source=('roots = ["src/my_project"]\ntests = ["tests"]\nselect = ["SF"]\n'),
                ),
                CliProjectFile(relative_path="tests/.gitkeep", source=""),
            ),
            expected_config_values=(
                ("roots", ("src/my_project",)),
                ("tests", ("tests",)),
                ("select", ("SF",)),
            ),
            expected_stdout_fragments=(
                "Empty repository",
                "Created src/my_project/__init__.py",
                "Created tests/",
                "Wrote strata.toml",
                "Found 0 faults",
            ),
            expected_stderr_fragments=(),
            expected_absent_output_fragments=("\x1b[",),
            expected_stdout_is_empty=False,
        ),
        InstalledInitCliTestCase(
            description="captured non-TTY invocation refuses unresolved interaction",
            argv=(),
            input_text="my-project\ny\n",
            initial_files=(),
            expected_exit_code=2,
            expected_files=(),
            expected_config_values=(),
            expected_stdout_fragments=(),
            expected_stderr_fragments=("requires a TTY", "--yes"),
            expected_absent_output_fragments=("Project name", "Accept?", "[Y/n]", "\x1b["),
            expected_stdout_is_empty=True,
        ),
        InstalledInitCliTestCase(
            description="full and gradual options are rejected by argparse",
            argv=("--full", "--gradual"),
            input_text="",
            initial_files=(),
            expected_exit_code=2,
            expected_files=(),
            expected_config_values=(),
            expected_stdout_fragments=(),
            expected_stderr_fragments=(
                "usage: strata init",
                "--gradual: not allowed with argument --full",
            ),
            expected_absent_output_fragments=("Project name", "Accept?", "\x1b["),
            expected_stdout_is_empty=True,
        ),
        InstalledInitCliTestCase(
            description="local config does not bypass argparse conflicts",
            argv=("--full", "--gradual"),
            input_text="",
            initial_files=(
                CliProjectFile(
                    relative_path="strata.toml",
                    source='roots = ["src/pkg"]\n',
                ),
            ),
            expected_exit_code=2,
            expected_files=(
                CliProjectFile(
                    relative_path="strata.toml",
                    source='roots = ["src/pkg"]\n',
                ),
            ),
            expected_config_values=(("roots", ("src/pkg",)),),
            expected_stdout_fragments=(),
            expected_stderr_fragments=("not allowed with argument --full",),
            expected_absent_output_fragments=("nothing to do",),
            expected_stdout_is_empty=True,
        ),
        InstalledInitCliTestCase(
            description="local config does not bypass argparse help",
            argv=("--help",),
            input_text="",
            initial_files=(
                CliProjectFile(
                    relative_path="strata.toml",
                    source='roots = ["src/pkg"]\n',
                ),
            ),
            expected_exit_code=0,
            expected_files=(
                CliProjectFile(
                    relative_path="strata.toml",
                    source='roots = ["src/pkg"]\n',
                ),
            ),
            expected_config_values=(("roots", ("src/pkg",)),),
            expected_stdout_fragments=("usage: strata init", "--help"),
            expected_stderr_fragments=(),
            expected_absent_output_fragments=("nothing to do",),
            expected_stdout_is_empty=False,
        ),
        InstalledInitCliTestCase(
            description="empty repository refuses explicit runtime scope",
            argv=("--yes", "--root", "src/example", "--no-skills"),
            input_text="",
            initial_files=(),
            expected_exit_code=2,
            expected_files=(),
            expected_config_values=(),
            expected_stdout_fragments=(),
            expected_stderr_fragments=(
                "--root, --tests, and --tooling options do not apply",
                "use --name",
            ),
            expected_absent_output_fragments=("Empty repository", "Created", "\x1b["),
            expected_stdout_is_empty=True,
        ),
    ],
    ids=lambda case: case.description,
)
def test_given_repository_state_when_running_installed_init_then_matches_contract(
    tmp_path: Path,
    test_case: InstalledInitCliTestCase,
) -> None:
    write_project_files(root=tmp_path, files=test_case.initial_files)

    completed: subprocess.CompletedProcess[str] = run_cli_init(
        root=tmp_path,
        argv=test_case.argv,
        input_text=test_case.input_text,
    )

    expected_snapshot: tuple[tuple[str, str], ...] = tuple(
        sorted((file.relative_path, file.source) for file in test_case.expected_files)
    )
    combined_output: str = completed.stdout + completed.stderr
    assert completed.returncode == test_case.expected_exit_code
    assert repository_text_snapshot(tmp_path) == expected_snapshot
    assert config_values(tmp_path) == test_case.expected_config_values
    assert all(fragment in completed.stdout for fragment in test_case.expected_stdout_fragments)
    assert all(fragment in completed.stderr for fragment in test_case.expected_stderr_fragments)
    assert all(
        fragment not in combined_output for fragment in test_case.expected_absent_output_fragments
    )
    assert (completed.stdout == "") is test_case.expected_stdout_is_empty
