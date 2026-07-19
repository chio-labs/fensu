"""Installed-console end-to-end tests for top-level CLI options."""

from __future__ import annotations

import subprocess
from importlib import metadata

import pytest

from tests.e2e.src.fensu.cli.main._test_types import InstalledEntryCliTestCase
from tests.e2e.src.fensu.cli.main.helpers import installed_fensu_executable


@pytest.mark.parametrize(
    "test_case",
    [
        InstalledEntryCliTestCase(
            description="installed help lists every top-level command",
            argv=("--help",),
            expected_exit_code=0,
            expected_stdout=(
                "Usage: fensu {init,check,rule,map,skills} ...\n\n"
                "Commands:\n"
                "  init    Initialize Fensu configuration for a repository.\n"
                "  check   Evaluate repository architecture rules.\n"
                "  rule    Show details for one rule.\n"
                "  map     Render a downstream project call map.\n"
                "  skills  Generate and install agent guidance.\n\n"
                "Run `fensu <command> --help` for command-specific options.\n"
            ),
            expected_stderr="",
        ),
        InstalledEntryCliTestCase(
            description="installed version matches distribution metadata",
            argv=("--version",),
            expected_exit_code=0,
            expected_stdout=f"fensu {metadata.version('fensu')}\n",
            expected_stderr="",
        ),
    ],
    ids=lambda case: case.description,
)
def test_given_top_level_option_when_running_installed_cli_then_matches_contract(
    test_case: InstalledEntryCliTestCase,
) -> None:
    completed: subprocess.CompletedProcess[str] = subprocess.run(
        (str(installed_fensu_executable()), *test_case.argv),
        capture_output=True,
        text=True,
        check=False,
    )

    assert completed.returncode == test_case.expected_exit_code
    assert completed.stdout == test_case.expected_stdout
    assert completed.stderr == test_case.expected_stderr
