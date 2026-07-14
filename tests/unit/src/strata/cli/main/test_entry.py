"""Tests for top-level CLI command dispatch."""

from __future__ import annotations

from unittest.mock import Mock

import pytest

from strata.cli.main import entry as entry_module
from tests.unit.src.strata.cli.main._test_types import EntryDispatchTestCase, EntryUsageTestCase


@pytest.mark.parametrize(
    "test_case",
    [
        EntryDispatchTestCase(
            description="init command delegates remaining arguments",
            argv=("init", "--yes", "--root", "src"),
            runner_attribute="run_init",
            expected_forwarded_argv=("--yes", "--root", "src"),
            expected_exit_code=17,
        ),
        EntryDispatchTestCase(
            description="rule command delegates remaining arguments",
            argv=("rule", "SFS131"),
            runner_attribute="run_rule",
            expected_forwarded_argv=("SFS131",),
            expected_exit_code=17,
        ),
        EntryDispatchTestCase(
            description="skills command delegates remaining arguments",
            argv=("skills", "--target", "agents"),
            runner_attribute="run_skills",
            expected_forwarded_argv=("--target", "agents"),
            expected_exit_code=17,
        ),
        EntryDispatchTestCase(
            description="map command delegates remaining arguments",
            argv=("map", "run", "--depth", "2"),
            runner_attribute="run_map",
            expected_forwarded_argv=("run", "--depth", "2"),
            expected_exit_code=17,
        ),
    ],
    ids=lambda case: case.description,
)
def test_given_subcommand_when_running_entry_then_delegates_remaining_arguments(
    monkeypatch: pytest.MonkeyPatch,
    test_case: EntryDispatchTestCase,
) -> None:
    forwarded_arguments: list[tuple[str, ...] | None] = []

    def record_command(*, argv: tuple[str, ...] | None = None) -> int:
        forwarded_arguments.append(argv)
        return test_case.expected_exit_code

    monkeypatch.setattr(entry_module, test_case.runner_attribute, record_command)

    exit_code: int = entry_module.main(test_case.argv)

    assert exit_code == test_case.expected_exit_code
    assert tuple(forwarded_arguments) == (test_case.expected_forwarded_argv,)


@pytest.mark.parametrize(
    "test_case",
    [
        EntryUsageTestCase(
            description="unknown command names rejected input and prints short usage",
            argv=("unknown",),
            expected_stdout="",
            expected_stderr=(
                "Unknown command: unknown\nUsage: strata {check,init,rule,skills,map} ...\n"
            ),
            expected_exit_code=2,
        ),
        EntryUsageTestCase(
            description="empty invocation prints short usage",
            argv=(),
            expected_stdout="",
            expected_stderr="Usage: strata {check,init,rule,skills,map} ...\n",
            expected_exit_code=2,
        ),
        EntryUsageTestCase(
            description="long help prints command summaries",
            argv=("--help",),
            expected_stdout=(
                "Usage: strata {init,check,rule,map,skills} ...\n\n"
                "Commands:\n"
                "  init    Initialize Strata configuration for a repository.\n"
                "  check   Evaluate repository architecture rules.\n"
                "  rule    Show details for one rule.\n"
                "  map     Render a downstream project call map.\n"
                "  skills  Generate and install agent guidance.\n\n"
                "Run `strata <command> --help` for command-specific options.\n"
            ),
            expected_stderr="",
            expected_exit_code=0,
        ),
        EntryUsageTestCase(
            description="short help matches long help",
            argv=("-h",),
            expected_stdout=(
                "Usage: strata {init,check,rule,map,skills} ...\n\n"
                "Commands:\n"
                "  init    Initialize Strata configuration for a repository.\n"
                "  check   Evaluate repository architecture rules.\n"
                "  rule    Show details for one rule.\n"
                "  map     Render a downstream project call map.\n"
                "  skills  Generate and install agent guidance.\n\n"
                "Run `strata <command> --help` for command-specific options.\n"
            ),
            expected_stderr="",
            expected_exit_code=0,
        ),
        EntryUsageTestCase(
            description="version prints installed distribution version",
            argv=("--version",),
            expected_stdout="strata 9.8.7\n",
            expected_stderr="",
            expected_exit_code=0,
        ),
    ],
    ids=lambda case: case.description,
)
def test_given_top_level_option_when_running_entry_then_writes_expected_output(
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
    test_case: EntryUsageTestCase,
) -> None:
    version: Mock = Mock(return_value="9.8.7")
    monkeypatch.setattr(entry_module.metadata, "version", version)

    exit_code: int = entry_module.main(test_case.argv)
    captured: tuple[str, str] = capsys.readouterr()

    assert exit_code == test_case.expected_exit_code
    assert captured[0] == test_case.expected_stdout
    assert captured[1] == test_case.expected_stderr


@pytest.mark.parametrize(
    "test_case",
    [
        EntryUsageTestCase(
            description="missing distribution metadata uses deterministic fallback",
            argv=("--version",),
            expected_stdout="strata unknown\n",
            expected_stderr="",
            expected_exit_code=0,
        )
    ],
    ids=lambda case: case.description,
)
def test_given_missing_distribution_when_reading_version_then_prints_unknown(
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
    test_case: EntryUsageTestCase,
) -> None:
    version: Mock = Mock(side_effect=entry_module.metadata.PackageNotFoundError("stratalint"))
    monkeypatch.setattr(entry_module.metadata, "version", version)

    exit_code: int = entry_module.main(test_case.argv)
    captured: tuple[str, str] = capsys.readouterr()

    assert exit_code == test_case.expected_exit_code
    assert captured[0] == test_case.expected_stdout
    assert captured[1] == test_case.expected_stderr
