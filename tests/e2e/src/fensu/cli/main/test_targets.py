"""Installed-console end-to-end tests for named analyzer targets."""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from tests.e2e.src.fensu.cli.main._test_types import (
    CliProjectFile,
    ConfigurableLayoutCliTestCase,
    InstalledEntryCliTestCase,
)
from tests.e2e.src.fensu.cli.main.helpers import (
    run_cli_check,
    run_configurable_layout_case,
)

_TARGET_CONFIG: str = (
    "[targets.core]\n"
    'analyzer = "python"\n'
    'roots = ["src/core"]\n'
    "tests = []\n"
    "tooling = []\n"
    'select = ["FFA101"]\n'
    "[targets.custom]\n"
    'analyzer = "python"\n'
    'root = "frontend"\n'
    'roots = ["src/custom"]\n'
    "tests = []\n"
    "tooling = []\n"
    'select = ["XNT001"]\n'
    'rule_paths = ["rules/named_target.py"]\n'
)
_TARGET_FILES: tuple[CliProjectFile, ...] = (
    CliProjectFile(relative_path="src/core/module.py", source="CORE: int = 1\n"),
    CliProjectFile(relative_path="frontend/src/custom/module.py", source="CUSTOM: int = 1\n"),
    CliProjectFile(
        relative_path="frontend/rules/named_target.py",
        source=(
            "import ast\n"
            "from fensu import Family, Fault, RuleContext, rule\n"
            "@rule(code='XNT001', family=Family.CUSTOM, slug='named-target', "
            "message='named target fault')\n"
            "def named_target(module: ast.Module, ctx: RuleContext) -> list[Fault]:\n"
            "    return [ctx.fault(node=module.body[0])]\n"
        ),
    ),
)


@pytest.mark.parametrize(
    "test_case",
    [
        ConfigurableLayoutCliTestCase(
            description="selected native target remains on the native check path",
            config=_TARGET_CONFIG,
            files=_TARGET_FILES,
            working_directory=".",
            argv=("check", "--no-color", "--no-cache", "--target", "core"),
            expected_exit_code=0,
            expected_stdout_fragments=("Found 0 faults",),
            expected_stderr_fragments=(),
        ),
        ConfigurableLayoutCliTestCase(
            description="selected custom target is forwarded to the Python host",
            config=_TARGET_CONFIG,
            files=_TARGET_FILES,
            working_directory=".",
            argv=("check", "--no-color", "--no-cache", "--target=custom"),
            expected_exit_code=1,
            expected_stdout_fragments=("XNT001", "frontend/src/custom/module.py"),
            expected_stderr_fragments=(),
        ),
        ConfigurableLayoutCliTestCase(
            description="installed check rejects ambiguous target selection",
            config=_TARGET_CONFIG,
            files=_TARGET_FILES,
            working_directory=".",
            argv=("check", "--no-color", "--no-cache"),
            expected_exit_code=2,
            expected_stdout_fragments=(),
            expected_stderr_fragments=("select one with --target TARGET",),
        ),
    ],
    ids=lambda case: case.description,
)
def test_given_named_targets_when_running_installed_check_then_routes_selected_analyzer(
    tmp_path: Path,
    test_case: ConfigurableLayoutCliTestCase,
) -> None:
    completed: subprocess.CompletedProcess[str] = run_configurable_layout_case(
        root=tmp_path, test_case=test_case
    )

    assert completed.returncode == test_case.expected_exit_code
    assert all(fragment in completed.stdout for fragment in test_case.expected_stdout_fragments)
    assert all(fragment in completed.stderr for fragment in test_case.expected_stderr_fragments)


@pytest.mark.parametrize(
    "test_case",
    [
        InstalledEntryCliTestCase(
            description="check help documents named target selection",
            argv=("--help",),
            expected_exit_code=0,
            expected_stdout="--target TARGET",
            expected_stderr="",
        )
    ],
    ids=lambda case: case.description,
)
def test_given_check_help_when_running_installed_cli_then_documents_target(
    tmp_path: Path, test_case: InstalledEntryCliTestCase
) -> None:
    (tmp_path / "fensu.toml").write_text('roots = ["src/pkg"]\n', encoding="utf-8")

    completed: subprocess.CompletedProcess[str] = run_cli_check(root=tmp_path, argv=test_case.argv)

    assert completed.returncode == test_case.expected_exit_code
    assert test_case.expected_stdout in completed.stdout
    assert completed.stderr == test_case.expected_stderr
