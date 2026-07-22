"""Installed-command coverage for post-check tree cleanup."""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from tests.e2e.src.fensu.cli.main._test_types import (
    CheckCleanupCliTestCase,
    CheckCleanupPreExecutionCliTestCase,
    CliProjectFile,
)
from tests.e2e.src.fensu.cli.main.helpers import run_cli_check, write_project_files


@pytest.mark.parametrize(
    "test_case",
    [
        CheckCleanupCliTestCase(
            description="core-only check cleans configured roots in the native process",
            config=(
                'roots = ["src/pkg"]\ntests = ["tests"]\ntooling = ["scripts"]\nselect = ["FFA"]\n'
            ),
            files=(CliProjectFile(relative_path="src/pkg/module.py", source="value: int = 1\n"),),
            expected_exit_code=0,
            expected_stdout_fragment="Found 0 faults",
        ),
        CheckCleanupCliTestCase(
            description="custom check cleans configured roots after the callback host exits",
            config=(
                'roots = ["src/pkg"]\n'
                'tests = ["tests"]\n'
                'tooling = ["scripts"]\n'
                'select = ["XCC001"]\n'
                'rule_paths = ["rules/custom.py"]\n'
            ),
            files=(
                CliProjectFile(relative_path="src/pkg/module.py", source="value: int = 1\n"),
                CliProjectFile(
                    relative_path="rules/custom.py",
                    source=(
                        "import ast\n"
                        "from fensu import Family, Fault, RuleContext, rule\n\n"
                        '@rule(code="XCC001", family=Family.CUSTOM, slug="cleanup", '
                        'message="custom cleanup fault")\n'
                        "def cleanup(module: ast.Module, ctx: RuleContext) -> list[Fault]:\n"
                        "    return [ctx.fault(node=module.body[0])]\n"
                    ),
                ),
            ),
            expected_exit_code=1,
            expected_stdout_fragment="XCC001",
        ),
    ],
    ids=lambda case: case.description,
)
def test_given_configured_cleanup_trees_when_check_finishes_then_only_disposable_trees_are_removed(
    tmp_path: Path,
    test_case: CheckCleanupCliTestCase,
) -> None:
    (tmp_path / "fensu.toml").write_text(test_case.config, encoding="utf-8")
    write_project_files(root=tmp_path, files=test_case.files)
    live_cache: Path = tmp_path / "src/pkg/__pycache__/module.cpython-312.pyc"
    live_cache.parent.mkdir(parents=True)
    live_cache.write_bytes(b"live cache")
    stale_cache: Path = tmp_path / "src/pkg/stale/__pycache__/removed.cpython-312.pyc"
    stale_cache.parent.mkdir(parents=True)
    stale_cache.write_bytes(b"stale cache")
    (tmp_path / "src/pkg/empty/nested").mkdir(parents=True)
    (tmp_path / "tests/empty/nested").mkdir(parents=True)
    (tmp_path / "scripts/empty/nested").mkdir(parents=True)
    outside_cache: Path = tmp_path / "outside/__pycache__/outside.pyc"
    outside_cache.parent.mkdir(parents=True)
    outside_cache.write_bytes(b"outside cache")

    completed: subprocess.CompletedProcess[str] = run_cli_check(
        root=tmp_path,
        argv=("--no-cache",),
    )

    assert completed.returncode == test_case.expected_exit_code
    assert test_case.expected_stdout_fragment in completed.stdout
    assert not (tmp_path / "src/pkg/stale").exists()
    assert not (tmp_path / "src/pkg/empty").exists()
    assert not (tmp_path / "tests/empty").exists()
    assert not (tmp_path / "scripts/empty").exists()
    assert live_cache.is_file()
    assert outside_cache.is_file()


@pytest.mark.parametrize(
    "test_case",
    [
        CheckCleanupPreExecutionCliTestCase(
            description="launched custom host argument errors remain read-only",
            config=('roots = ["src/pkg"]\nselect = ["XCC001"]\nrule_paths = ["rules/custom.py"]\n'),
            files=(
                CliProjectFile(relative_path="src/pkg/module.py", source="value: int = 1\n"),
                CliProjectFile(
                    relative_path="rules/custom.py",
                    source=(
                        "import ast\n"
                        "from fensu import Family, Fault, RuleContext, rule\n\n"
                        '@rule(code="XCC001", family=Family.CUSTOM, slug="cleanup", '
                        'message="custom cleanup fault")\n'
                        "def cleanup(module: ast.Module, ctx: RuleContext) -> list[Fault]:\n"
                        "    return [ctx.fault(node=module.body[0])]\n"
                    ),
                ),
            ),
            argv=("--unknown",),
            expected_exit_code=2,
            expected_path="src/pkg/empty/nested",
        )
    ],
    ids=lambda case: case.description,
)
def test_given_custom_host_pre_execution_exit_when_checking_then_repository_is_not_cleaned(
    tmp_path: Path,
    test_case: CheckCleanupPreExecutionCliTestCase,
) -> None:
    (tmp_path / "fensu.toml").write_text(test_case.config, encoding="utf-8")
    write_project_files(root=tmp_path, files=test_case.files)
    preserved: Path = tmp_path / test_case.expected_path
    preserved.mkdir(parents=True)

    completed: subprocess.CompletedProcess[str] = run_cli_check(
        root=tmp_path,
        argv=test_case.argv,
    )

    assert completed.returncode == test_case.expected_exit_code
    assert preserved.is_dir()
