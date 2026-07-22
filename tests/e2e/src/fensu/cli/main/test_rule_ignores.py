"""Installed custom-host parity for path-scoped rule ignores."""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from tests.e2e.src.fensu.cli.main._test_types import CliProjectFile, RuleIgnoreCliTestCase
from tests.e2e.src.fensu.cli.main.helpers import run_cli_check, write_project_files


@pytest.mark.parametrize(
    "test_case",
    [
        RuleIgnoreCliTestCase(
            description="custom rule retains project context and filters by reported path",
            config=(
                'roots = ["src/pkg"]\n'
                "tests = []\n"
                "tooling = []\n"
                'select = ["XRI001"]\n'
                'rule_paths = ["rules/custom.py"]\n\n'
                "[[rule_ignores]]\n"
                'rules = ["XRI"]\n'
                'paths = ["src/pkg/{generated,vendored}.py"]\n'
                'reason = "Generated interface findings are accepted."\n'
            ),
            files=(
                CliProjectFile(relative_path="src/pkg/live.py", source="value: int = 1\n"),
                CliProjectFile(relative_path="src/pkg/generated.py", source="value: int = 2\n"),
                CliProjectFile(
                    relative_path="src/pkg/{generated,vendored}.py",
                    source="value: int = 3\n",
                ),
                CliProjectFile(
                    relative_path="rules/custom.py",
                    source=(
                        "import ast\n"
                        "from fensu import Family, Fault, RuleContext, rule\n\n"
                        '@rule(code="XRI001", family=Family.CUSTOM, slug="reported-path", '
                        'message="reported path")\n'
                        "def reported_path(module: ast.Module, ctx: RuleContext) -> list[Fault]:\n"
                        "    del module\n"
                        "    generated = ctx.repo_root / 'src/pkg/generated.py'\n"
                        "    literal = ctx.repo_root / 'src/pkg/{generated,vendored}.py'\n"
                        "    if ctx.path.name != 'live.py':\n"
                        "        return []\n"
                        "    exists = ctx.project.exists(requester=ctx.path, path=generated)\n"
                        "    return [\n"
                        "        ctx.fault_for(path=generated, line=1, column=0),\n"
                        "        ctx.fault_for(path=literal, line=1, column=0),\n"
                        "        ctx.path_fault(message=f'context-visible={exists}'),\n"
                        "    ]\n"
                    ),
                ),
            ),
            expected_exit_code=1,
            expected_present_fragments=("context-visible=True", "src/pkg/generated.py:1:0"),
            expected_absent_fragment="src/pkg/{generated,vendored}.py:1:0",
        )
    ],
    ids=lambda case: case.description,
)
def test_given_custom_reported_path_when_rule_ignore_matches_then_context_remains_available(
    tmp_path: Path,
    test_case: RuleIgnoreCliTestCase,
) -> None:
    (tmp_path / "fensu.toml").write_text(test_case.config, encoding="utf-8")
    write_project_files(root=tmp_path, files=test_case.files)

    completed: subprocess.CompletedProcess[str] = run_cli_check(
        root=tmp_path,
        argv=("--no-cache",),
    )

    assert completed.returncode == test_case.expected_exit_code
    assert all(fragment in completed.stdout for fragment in test_case.expected_present_fragments)
    assert test_case.expected_absent_fragment not in completed.stdout
