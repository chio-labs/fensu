"""Tests for named targets in the Python custom-rule check host."""

from __future__ import annotations

from pathlib import Path

import pytest

from fensu.cli.main.custom_check_host import run_custom_check as run_check
from tests.integration.src.fensu.cli.main._test_types import TargetCheckTestCase
from tests.integration.src.fensu.cli.main.helpers import CaptureOutput


@pytest.mark.parametrize(
    "test_case",
    [
        TargetCheckTestCase(
            description="selected custom-rule target evaluates repository-relative source",
            argv=("--no-color", "--no-cache", "--target", "custom"),
            expected_exit_code=1,
            expected_stdout_fragment="XNT001  named target fault\n --> src/custom/module.py:1:0",
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
        'root = "."\n'
        'roots = ["src/custom"]\n'
        "tests = []\n"
        'select = ["XNT001"]\n'
        'rule_paths = ["rules/named_target.py"]\n',
        encoding="utf-8",
    )
    core: Path = tmp_path / "src/core/module.py"
    core.parent.mkdir(parents=True)
    core.write_text("CORE: int = 1\n", encoding="utf-8")
    custom: Path = tmp_path / "src/custom/module.py"
    custom.parent.mkdir(parents=True)
    custom.write_text("CUSTOM: int = 1\n", encoding="utf-8")
    rule: Path = tmp_path / "rules/named_target.py"
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
    monkeypatch.chdir(tmp_path)
    stdout: CaptureOutput = CaptureOutput()
    stderr: CaptureOutput = CaptureOutput()

    exit_code: int = run_check(argv=test_case.argv, stdout=stdout, stderr=stderr)

    assert exit_code == test_case.expected_exit_code
    assert test_case.expected_stdout_fragment in stdout.getvalue()
    assert test_case.expected_stderr_fragment in stderr.getvalue()
