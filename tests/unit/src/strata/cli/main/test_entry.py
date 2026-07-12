"""Tests for top-level CLI command dispatch."""

from __future__ import annotations

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
            argv=("skills", "update", "--target", "agents"),
            runner_attribute="run_skills",
            expected_forwarded_argv=("update", "--target", "agents"),
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
            description="unknown command prints usage containing init",
            argv=("unknown",),
            expected_usage="Usage: strata {check,init,rule,skills,map} ...\n",
            expected_exit_code=2,
        )
    ],
    ids=lambda case: case.description,
)
def test_given_unknown_command_when_running_entry_then_usage_includes_init(
    capsys: pytest.CaptureFixture[str],
    test_case: EntryUsageTestCase,
) -> None:
    exit_code: int = entry_module.main(test_case.argv)

    assert exit_code == test_case.expected_exit_code
    assert capsys.readouterr().err == test_case.expected_usage
