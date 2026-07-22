"""Installed checks for composable custom-rule test conventions."""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from tests.e2e.src.fensu.cli.main._test_types import (
    CliProjectFile,
    CustomRuleCompositionCliTestCase,
)
from tests.e2e.src.fensu.cli.main.helpers import run_cli_check, write_project_files

_WRAPPER_SOURCE: str = """import pytest

from fensu import RuleCase, RuleResult, evaluate_rule
from scripts.fensu_policy.rules.client_ownership import no_global_client
from tests.unit.scripts.fensu_policy.rules._test_types import CustomRuleTestCase


@pytest.mark.parametrize(
    "test_case",
    [
        CustomRuleTestCase(
            description="reports forbidden behavior",
            path="package/example.py",
            source="GLOBAL_CLIENT = build_client()\\n",
            expected_fault_count=1,
        )
    ],
    ids=lambda case: case.description,
)
def test_given_source_when_checking_rule_then_returns_expected_faults(
    test_case: CustomRuleTestCase,
) -> None:
    result: RuleResult = evaluate_rule(
        rule=no_global_client,
        test_case=RuleCase(
            description=test_case.description,
            path=test_case.path,
            source=test_case.source,
            expected_fault_count=test_case.expected_fault_count,
            files=test_case.files,
            scope=test_case.scope,
            scope_root=test_case.scope_root,
        ),
    )

    assert result.fault_count == test_case.expected_fault_count
"""

_DIRECT_SOURCE: str = """import pytest

from fensu import RuleCase, RuleResult, evaluate_rule
from scripts.fensu_policy.rules.client_ownership import no_global_client


@pytest.mark.parametrize(
    "test_case",
    [
        RuleCase(
            description="reports forbidden behavior",
            path="package/example.py",
            source="GLOBAL_CLIENT = build_client()\\n",
            expected_fault_count=1,
        )
    ],
    ids=lambda case: case.description,
)
def test_given_source_when_checking_rule_then_returns_expected_faults(
    test_case: RuleCase,
) -> None:
    result: RuleResult = evaluate_rule(rule=no_global_client, test_case=test_case)

    assert result.fault_count == test_case.expected_fault_count
"""

_TEST_TYPES_SOURCE: str = """from dataclasses import dataclass

from fensu import RuleFile


@dataclass(frozen=True)
class CustomRuleTestCase:
    description: str
    path: str
    source: str
    expected_fault_count: int
    files: tuple[RuleFile, ...] = ()
    scope: str = "root"
    scope_root: str | None = None
"""


@pytest.mark.parametrize(
    "test_case",
    [
        CustomRuleCompositionCliTestCase(
            description="local wrapper composes custom coverage and test policies",
            test_source=_WRAPPER_SOURCE,
            expected_exit_code=0,
            expected_present_codes=(),
            expected_absent_codes=("FFR707", "FFT204", "FFT413"),
        ),
        CustomRuleCompositionCliTestCase(
            description="direct RuleCase parameterization remains an FFT413 violation",
            test_source=_DIRECT_SOURCE,
            expected_exit_code=1,
            expected_present_codes=("FFT413",),
            expected_absent_codes=("FFR707", "FFT204"),
        ),
    ],
    ids=lambda case: case.description,
)
def test_given_custom_rule_test_pattern_when_checking_then_policies_compose_as_documented(
    tmp_path: Path,
    test_case: CustomRuleCompositionCliTestCase,
) -> None:
    config: str = (
        'roots = ["src/pkg"]\n'
        'tests = ["tests"]\n'
        'tooling = ["scripts"]\n'
        'select = ["FFR707", "FFT204", "FFT413"]\n'
        'rule_paths = ["scripts/fensu_policy/rules/client_ownership.py"]\n'
    )
    files: tuple[CliProjectFile, ...] = (
        CliProjectFile(relative_path="src/pkg/module.py", source="value: int = 1\n"),
        CliProjectFile(
            relative_path="scripts/fensu_policy/rules/client_ownership.py",
            source=(
                "import ast\n"
                "from fensu import Family, Fault, RuleContext, rule\n\n"
                '@rule(code="XCO001", family=Family.CUSTOM, slug="client", '
                'message="global client")\n'
                "def no_global_client(module: ast.Module, ctx: RuleContext) -> list[Fault]:\n"
                "    return [ctx.path_fault()] if module.body else []\n"
            ),
        ),
        CliProjectFile(
            relative_path="tests/unit/scripts/fensu_policy/rules/_test_types.py",
            source=_TEST_TYPES_SOURCE,
        ),
        CliProjectFile(
            relative_path="tests/unit/scripts/fensu_policy/rules/test_client_ownership.py",
            source=test_case.test_source,
        ),
    )
    (tmp_path / "fensu.toml").write_text(config, encoding="utf-8")
    write_project_files(root=tmp_path, files=files)

    completed: subprocess.CompletedProcess[str] = run_cli_check(
        root=tmp_path,
        argv=("--no-cache",),
    )

    assert completed.returncode == test_case.expected_exit_code
    assert all(code in completed.stdout for code in test_case.expected_present_codes)
    assert all(code not in completed.stdout for code in test_case.expected_absent_codes)
