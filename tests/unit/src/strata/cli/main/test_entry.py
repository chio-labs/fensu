"""Tests for top-level CLI command dispatch."""

from __future__ import annotations

import pytest

from strata.cli.main import entry as entry_module
from tests.unit.src.strata.cli.main._test_types import EntryDispatchTestCase


@pytest.mark.parametrize(
    "test_case",
    [
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
