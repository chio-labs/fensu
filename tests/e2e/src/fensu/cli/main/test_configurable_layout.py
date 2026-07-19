"""End-to-end checks for authoritative configurable project layouts."""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from tests.e2e.src.fensu.cli.main._test_types import (
    CliProjectFile,
    ConfigurableLayoutCliTestCase,
)
from tests.e2e.src.fensu.cli.main.helpers import run_configurable_layout_case


@pytest.mark.parametrize(
    "test_case",
    [
        ConfigurableLayoutCliTestCase(
            description="python package root preserves layer enforcement",
            config=('roots = ["python/mypkg"]\ntests = []\ntooling = []\nselect = ["FFL101"]\n'),
            files=(
                CliProjectFile(
                    relative_path="python/mypkg/domain/alpha/main/run.py",
                    source="from mypkg.domain.beta._helpers.parse import parse_value\n",
                ),
            ),
            working_directory=".",
            expected_exit_code=1,
            expected_stdout_fragments=(
                "FFL101",
                "python/mypkg/domain/alpha/main/run.py:1:0",
                "reaches into sibling internals",
            ),
            expected_stderr_fragments=(),
        ),
        ConfigurableLayoutCliTestCase(
            description="nested tooling package preserves runtime boundary",
            config=(
                'roots = ["python/mypkg"]\n'
                "tests = []\n"
                'tooling = ["dev/tools"]\n'
                'select = ["FFL301"]\n'
            ),
            files=(
                CliProjectFile(
                    relative_path="python/mypkg/domain/alpha/main/run.py",
                    source="from tools.release import publish\n",
                ),
                CliProjectFile(
                    relative_path="dev/tools/release.py",
                    source="def publish() -> None:\n    pass\n",
                ),
            ),
            working_directory=".",
            expected_exit_code=1,
            expected_stdout_fragments=("FFL301", "python/mypkg/domain/alpha/main/run.py:1:0"),
            expected_stderr_fragments=(),
        ),
        ConfigurableLayoutCliTestCase(
            description="project result resolution follows unconventional source root",
            config=('roots = ["python/mypkg"]\ntests = []\ntooling = []\nselect = ["FFS101"]\n'),
            files=(
                CliProjectFile(
                    relative_path="python/mypkg/domain/core/main/run.py",
                    source=(
                        "from mypkg.domain.core._helpers.phase import build_value\n\n\n"
                        "def run() -> None:\n"
                        "    build_value()\n"
                    ),
                ),
                CliProjectFile(
                    relative_path="python/mypkg/domain/core/_helpers/phase.py",
                    source="def build_value() -> int:\n    return 1\n",
                ),
            ),
            working_directory=".",
            expected_exit_code=1,
            expected_stdout_fragments=("FFS101", "python/mypkg/domain/core/main/run.py:5:4"),
            expected_stderr_fragments=(),
        ),
        ConfigurableLayoutCliTestCase(
            description="custom test root accepts exact configured source mirror",
            config=(
                'roots = ["python/mypkg"]\n'
                'tests = ["qa"]\n'
                "tooling = []\n"
                'select = ["FFT001", "FFT002", "FFT003", "FFT004", '
                '"FFT005", "FFT006", "FFT007", "FFT008"]\n'
            ),
            files=(
                CliProjectFile(
                    relative_path="python/mypkg/domain/__init__.py",
                    source="",
                ),
                CliProjectFile(
                    relative_path="qa/unit/python/mypkg/domain/test_example.py",
                    source="",
                ),
            ),
            working_directory=".",
            expected_exit_code=0,
            expected_stdout_fragments=("Found 0 faults",),
            expected_stderr_fragments=(),
        ),
        ConfigurableLayoutCliTestCase(
            description="narrow test root wins over broad runtime root",
            config=('roots = ["."]\ntests = ["qa"]\ntooling = []\nselect = ["FFT301"]\n'),
            files=(CliProjectFile(relative_path="qa/unit/bad.py", source=""),),
            working_directory=".",
            expected_exit_code=1,
            expected_stdout_fragments=("FFT301", "qa/unit/bad.py"),
            expected_stderr_fragments=(),
        ),
        ConfigurableLayoutCliTestCase(
            description="nested invocation finds config roots and relative custom rules",
            config=(
                'roots = ["python/mypkg"]\n'
                "tests = []\n"
                "tooling = []\n"
                'rule_paths = ["rules/custom.py"]\n'
                'select = ["XEDB"]\n'
            ),
            files=(
                CliProjectFile(
                    relative_path="python/mypkg/target.py",
                    source="VALUE: int = 1\n",
                ),
                CliProjectFile(
                    relative_path="rules/custom.py",
                    source=(
                        "from __future__ import annotations\n\n"
                        "import ast\n\n"
                        "from fensu import Family, Fault, RuleContext, Threshold, rule\n\n"
                        "@rule(code='XEDB2001', family=Family.ROLES, slug='e2e', message='e2e fault')\n"
                        "def check(module: ast.Module, ctx: RuleContext) -> list[Fault]:\n"
                        "    _ = ctx.threshold(name=Threshold.MAX_STATEMENTS)\n"
                        "    return [ctx.fault(node=module.body[0])]\n"
                    ),
                ),
            ),
            working_directory="python/mypkg/nested",
            expected_exit_code=1,
            expected_stdout_fragments=("XEDB2001", "python/mypkg/target.py:1:0", "e2e fault"),
            expected_stderr_fragments=(),
        ),
        ConfigurableLayoutCliTestCase(
            description="ambiguous runtime and tooling import package fails loudly",
            config=('roots = ["src/tools"]\ntests = []\ntooling = ["dev/tools"]\n'),
            files=(
                CliProjectFile(relative_path="src/tools/__init__.py", source=""),
                CliProjectFile(relative_path="dev/tools/__init__.py", source=""),
            ),
            working_directory=".",
            expected_exit_code=2,
            expected_stdout_fragments=(),
            expected_stderr_fragments=("must not claim the same import package: tools",),
        ),
        ConfigurableLayoutCliTestCase(
            description="positional paths remain relative to the invocation directory",
            config=('roots = ["python/mypkg"]\ntests = []\ntooling = []\nselect = ["FFA101"]\n'),
            files=(
                CliProjectFile(
                    relative_path="python/mypkg/domain/alpha/good.py",
                    source="VALUE: int = 1\n",
                ),
                CliProjectFile(
                    relative_path="python/mypkg/domain/beta/bad.py",
                    source="VALUE = 1\n",
                ),
            ),
            working_directory="python/mypkg/domain/alpha",
            expected_exit_code=0,
            expected_stdout_fragments=("Found 0 faults",),
            expected_stderr_fragments=(),
            argv=("check", "--no-color", "."),
        ),
    ],
    ids=lambda case: case.description,
)
def test_given_configurable_project_when_running_console_check_then_honors_layout_contract(
    tmp_path: Path,
    test_case: ConfigurableLayoutCliTestCase,
) -> None:
    completed: subprocess.CompletedProcess[str] = run_configurable_layout_case(
        root=tmp_path,
        test_case=test_case,
    )

    assert completed.returncode == test_case.expected_exit_code
    assert all(fragment in completed.stdout for fragment in test_case.expected_stdout_fragments)
    assert all(fragment in completed.stderr for fragment in test_case.expected_stderr_fragments)
