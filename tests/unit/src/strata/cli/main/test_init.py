"""Tests for the thin strata init CLI adapter."""

from __future__ import annotations

from io import StringIO
from pathlib import Path
from typing import TextIO
from unittest.mock import Mock

import pytest

from strata.cli.main import _init as init_module
from strata.scaffolding.models import InitOptions
from tests.unit.src.strata.cli.main._test_types import InitAdapterTestCase, InitNoColorTestCase


@pytest.mark.parametrize(
    "test_case",
    [
        InitAdapterTestCase(
            description="unanswered choices remain absent",
            argv=(),
            stdout_isatty=False,
            expected_options=InitOptions(),
            expected_use_color=False,
            expected_exit_code=17,
        ),
        InitAdapterTestCase(
            description="explicit options are translated and repeated paths are flattened",
            argv=(
                "--yes",
                "--root",
                "src",
                "packages/a",
                "--root",
                "packages/b",
                "--tests",
                "tests/unit",
                "tests/integration",
                "--tests",
                "tests/e2e",
                "--tooling",
                "scripts",
                "tools",
                "--skills",
                "--memory",
                "--name",
                "sample",
            ),
            stdout_isatty=True,
            expected_options=InitOptions(
                yes=True,
                roots=("src", "packages/a", "packages/b"),
                tests=("tests/unit", "tests/integration", "tests/e2e"),
                tooling=("scripts", "tools"),
                skills=True,
                memory=True,
                name="sample",
            ),
            expected_use_color=True,
            expected_exit_code=17,
        ),
        InitAdapterTestCase(
            description="disabled skills remain explicit",
            argv=("--no-skills",),
            stdout_isatty=True,
            expected_options=InitOptions(
                skills=False,
            ),
            expected_use_color=True,
            expected_exit_code=17,
        ),
    ],
    ids=lambda case: case.description,
)
def test_given_init_arguments_when_running_adapter_then_delegates_typed_options(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    test_case: InitAdapterTestCase,
) -> None:
    stdin: TextIO = StringIO()
    stdout: Mock = Mock(spec=TextIO)
    stdout.isatty.return_value = test_case.stdout_isatty
    stderr: TextIO = StringIO()
    home_dir: Path = tmp_path / "home"
    working_directory: Path = tmp_path / "nested" / ".."
    repositories: list[Path] = []
    stdins: list[TextIO] = []
    stdouts: list[TextIO] = []
    stderrs: list[TextIO] = []
    delegated_options: list[InitOptions] = []
    color_choices: list[bool] = []
    home_directories: list[Path | None] = []

    def record_init(
        *,
        repository: Path,
        stdin: TextIO,
        stdout: TextIO,
        stderr: TextIO,
        options: InitOptions,
        use_color: bool,
        home_dir: Path | None = None,
    ) -> int:
        repositories.append(repository)
        stdins.append(stdin)
        stdouts.append(stdout)
        stderrs.append(stderr)
        delegated_options.append(options)
        color_choices.append(use_color)
        home_directories.append(home_dir)
        return test_case.expected_exit_code

    monkeypatch.delenv("NO_COLOR", raising=False)
    monkeypatch.setattr(init_module, "_run_init", record_init)

    exit_code: int = init_module.run_init(
        argv=test_case.argv,
        stdin=stdin,
        stdout=stdout,
        stderr=stderr,
        working_directory=working_directory,
        home_dir=home_dir,
    )

    assert exit_code == test_case.expected_exit_code
    assert tuple(repositories) == (working_directory.resolve(),)
    assert tuple(stdins) == (stdin,)
    assert tuple(stdouts) == (stdout,)
    assert tuple(stderrs) == (stderr,)
    assert tuple(delegated_options) == (test_case.expected_options,)
    assert tuple(color_choices) == (test_case.expected_use_color,)
    assert tuple(home_directories) == (home_dir,)


@pytest.mark.parametrize(
    "test_case",
    [
        InitNoColorTestCase(
            description="NO_COLOR disables color on a terminal",
            no_color="1",
            expected_use_color=False,
            expected_exit_code=17,
        )
    ],
    ids=lambda case: case.description,
)
def test_given_no_color_environment_when_running_init_then_delegates_plain_output(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    test_case: InitNoColorTestCase,
) -> None:
    stdout: Mock = Mock(spec=TextIO)
    stdout.isatty.return_value = True
    color_choices: list[bool] = []

    def record_init(
        *,
        repository: Path,
        stdin: TextIO,
        stdout: TextIO,
        stderr: TextIO,
        options: InitOptions,
        use_color: bool,
        home_dir: Path | None = None,
    ) -> int:
        color_choices.append(use_color)
        return test_case.expected_exit_code

    monkeypatch.setenv("NO_COLOR", test_case.no_color)
    monkeypatch.setattr(init_module, "_run_init", record_init)

    exit_code: int = init_module.run_init(stdout=stdout, working_directory=tmp_path)

    assert exit_code == test_case.expected_exit_code
    assert tuple(color_choices) == (test_case.expected_use_color,)
