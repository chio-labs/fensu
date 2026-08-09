"""Tests for named targets in the Python custom-rule check host."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

from fensu.cli.main.custom_check_host import run_custom_check as run_check
from tests.integration.src.fensu.cli.main._test_types import (
    CanonicalAliasCheckTestCase,
    TargetCheckTestCase,
)
from tests.integration.src.fensu.cli.main.helpers import CaptureOutput


@pytest.mark.skipif(sys.platform == "win32", reason="symlink creation requires Windows privileges")
@pytest.mark.parametrize(
    "test_case",
    [
        CanonicalAliasCheckTestCase(
            description="Python diagnostics match Rust canonical alias behavior",
            expected_exit_code=1,
            expected_present="canonical/src/pkg/module.py",
            expected_alias_absent="alias/src/pkg/module.py",
            expected_double_prefix_absent="canonical/canonical/",
            expected_stderr="",
        )
    ],
    ids=lambda case: case.description,
)
def test_given_internal_target_alias_when_checking_then_reports_canonical_prefix_once(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    test_case: CanonicalAliasCheckTestCase,
) -> None:
    (tmp_path / "fensu.toml").write_text(
        "[targets.app]\n"
        'analyzer = "python"\n'
        'root = "alias"\n'
        'roots = ["src/pkg"]\n'
        "tests = []\n"
        "tooling = []\n"
        'select = ["FFA101"]\n',
        encoding="utf-8",
    )
    source: Path = tmp_path / "canonical/src/pkg/module.py"
    source.parent.mkdir(parents=True)
    source.write_text("VALUE = 1\n", encoding="utf-8")
    (tmp_path / "alias").symlink_to(tmp_path / "canonical", target_is_directory=True)
    monkeypatch.chdir(tmp_path)
    stdout: CaptureOutput = CaptureOutput()
    stderr: CaptureOutput = CaptureOutput()

    exit_code: int = run_check(
        argv=("--no-color", "--no-cache", "--target", "app"),
        stdout=stdout,
        stderr=stderr,
    )
    output: str = stdout.getvalue()

    assert exit_code == test_case.expected_exit_code
    assert test_case.expected_present in output
    assert test_case.expected_alias_absent not in output
    assert test_case.expected_double_prefix_absent not in output
    assert stderr.getvalue() == test_case.expected_stderr


@pytest.mark.parametrize(
    "test_case",
    [
        TargetCheckTestCase(
            description="selected custom-rule target evaluates repository-relative source",
            argv=("--no-color", "--no-cache", "--target", "custom"),
            expected_exit_code=1,
            expected_stdout_fragment=(
                "XNT001  named target fault\n --> frontend/scripts/tool.py:1:0"
            ),
            expected_stderr_fragment="",
        ),
        TargetCheckTestCase(
            description="multiple custom-host targets require explicit selection",
            argv=("--no-color", "--no-cache"),
            expected_exit_code=2,
            expected_stdout_fragment="",
            expected_stderr_fragment="select one with --target TARGET",
        ),
        TargetCheckTestCase(
            description="unknown custom-host target is rejected",
            argv=("--no-color", "--no-cache", "--target", "missing"),
            expected_exit_code=2,
            expected_stdout_fragment="",
            expected_stderr_fragment="Unknown target name: missing",
        ),
        TargetCheckTestCase(
            description="Python host reads target-local pyproject entrypoints",
            argv=("--no-color", "--no-cache", "--target", "metadata"),
            expected_exit_code=0,
            expected_stdout_fragment="Found 0 faults",
            expected_stderr_fragment="",
        ),
        TargetCheckTestCase(
            description="Python host applies target-local symbol exception without staleness",
            argv=("--no-color", "--no-cache", "--target", "symbol-exception"),
            expected_exit_code=1,
            expected_stdout_fragment="exceptions-symbol/src/pkg/external.py:5:",
            expected_stderr_fragment="",
        ),
        TargetCheckTestCase(
            description="Python host applies target-local file exception without staleness",
            argv=("--no-color", "--no-cache", "--target", "file-exception"),
            expected_exit_code=0,
            expected_stdout_fragment="Applied 1 rule exception",
            expected_stderr_fragment="",
        ),
    ],
    ids=lambda case: case.description,
)
def test_given_named_targets_when_running_custom_host_then_uses_same_selection_semantics(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    test_case: TargetCheckTestCase,
) -> None:
    (tmp_path / "fensu.toml").write_text(
        "[targets.core]\n"
        'analyzer = "python"\n'
        'roots = ["src/core"]\n'
        "tests = []\n"
        'select = ["FFA101"]\n'
        "[targets.custom]\n"
        'analyzer = "python"\n'
        'root = "frontend"\n'
        'roots = ["src/custom"]\n'
        'tests = ["tests"]\n'
        'tooling = ["scripts"]\n'
        'select = ["XNT001"]\n'
        'rule_paths = ["rules/named_target.py"]\n'
        "[targets.metadata]\n"
        'analyzer = "python"\n'
        'root = "metadata"\n'
        'roots = ["src/pkg"]\n'
        "tests = []\n"
        "tooling = []\n"
        'select = ["FFL105"]\n'
        "[targets.symbol-exception]\n"
        'analyzer = "python"\n'
        'root = "exceptions-symbol"\n'
        'roots = ["src/pkg"]\n'
        "tests = []\n"
        "tooling = []\n"
        'select = ["FFS120"]\n'
        "[targets.symbol-exception.thresholds]\n"
        "max_positional_args = 0\n"
        "[[targets.symbol-exception.rule_exceptions]]\n"
        'rule = "FFS120"\n'
        'path = "src/pkg/external.py"\n'
        'symbols = ["callback"]\n'
        'reason = "External callback remains positional."\n'
        "[targets.file-exception]\n"
        'analyzer = "python"\n'
        'root = "exceptions-file"\n'
        'roots = ["src/pkg"]\n'
        "tests = []\n"
        "tooling = []\n"
        'select = ["FFA001"]\n'
        "[[targets.file-exception.rule_exceptions]]\n"
        'rule = "FFA001"\n'
        'path = "src/pkg/external.py"\n'
        'reason = "Accepted file callback."\n',
        encoding="utf-8",
    )
    core: Path = tmp_path / "src/core/module.py"
    core.parent.mkdir(parents=True)
    core.write_text("CORE: int = 1\n", encoding="utf-8")
    custom: Path = tmp_path / "frontend/src/custom/module.py"
    custom.parent.mkdir(parents=True)
    custom.write_text("CUSTOM: int = 1\n", encoding="utf-8")
    target_test: Path = tmp_path / "frontend/tests/test_module.py"
    target_test.parent.mkdir(parents=True)
    target_test.write_text("TEST_VALUE: int = 1\n", encoding="utf-8")
    target_tool: Path = tmp_path / "frontend/scripts/tool.py"
    target_tool.parent.mkdir(parents=True)
    target_tool.write_text("TOOL_VALUE: int = 1\n", encoding="utf-8")
    rule: Path = tmp_path / "frontend/rules/named_target.py"
    rule.parent.mkdir()
    rule.write_text(
        "import ast\n"
        "from fensu import Family, Fault, RuleContext, rule\n"
        "@rule(code='XNT001', family=Family.CUSTOM, slug='named-target', "
        "message='named target fault')\n"
        "def named_target(module: ast.Module, ctx: RuleContext) -> list[Fault]:\n"
        "    return [ctx.fault(node=module.body[0])]\n",
        encoding="utf-8",
    )
    entry: Path = tmp_path / "metadata/src/pkg/orders/main/run.py"
    entry.parent.mkdir(parents=True)
    entry.write_text("def run() -> None:\n    pass\n", encoding="utf-8")
    (tmp_path / "metadata/pyproject.toml").write_text(
        "[project]\n"
        'name = "metadata"\n'
        'version = "0.0.0"\n'
        "[project.scripts]\n"
        'run = "pkg.orders.main.run:run"\n',
        encoding="utf-8",
    )
    symbol_exception: Path = tmp_path / "exceptions-symbol/src/pkg/external.py"
    symbol_exception.parent.mkdir(parents=True)
    symbol_exception.write_text(
        "def callback(value: int) -> None:\n"
        "    return None\n\n\n"
        "def retained(value: int) -> None:\n"
        "    return None\n",
        encoding="utf-8",
    )
    file_exception: Path = tmp_path / "exceptions-file/src/pkg/external.py"
    file_exception.parent.mkdir(parents=True)
    file_exception.write_text(
        "def callback(value):\n    return value\n",
        encoding="utf-8",
    )
    monkeypatch.chdir(tmp_path)
    stdout: CaptureOutput = CaptureOutput()
    stderr: CaptureOutput = CaptureOutput()

    exit_code: int = run_check(argv=test_case.argv, stdout=stdout, stderr=stderr)

    assert exit_code == test_case.expected_exit_code
    assert test_case.expected_stdout_fragment in stdout.getvalue()
    assert test_case.expected_stderr_fragment in stderr.getvalue()
