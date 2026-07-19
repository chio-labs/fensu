"""Tests for tests-family rules."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from unittest.mock import Mock

import pytest

from fensu.analysis.models import SourceLocation
from fensu.config.models import Config
from fensu.discovery.main.discover_files import discover_files
from fensu.discovery.models import ScopedFile
from fensu.evaluation._helpers.parsing import parse_scoped_file
from fensu.evaluation.main.evaluate import evaluate
from fensu.evaluation.models import EvaluationResult, ParsedModule
from fensu.rules.authoring.types import RuleContext
from fensu.rules.tests._helpers import checks as test_checks
from fensu.rules.tests.constants import FFT_RULES
from fensu.rules.tests.main import _testing_rules as testing_rules_module
from fensu.rules.tests.types import FftCode
from tests.unit.src.fensu.rules.tests.main._test_types import (
    FftConfiguredLayoutTestCase,
    FftOperationTestCase,
    FftRuleFile,
    FftRuleTestCase,
)
from tests.unit.src.fensu.rules.tests.main.helpers import (
    GOOD_TEST_SOURCE,
    GOOD_TEST_TYPES_SOURCE,
    evaluate_configured_layout_test_case,
    evaluate_tests_rule_test_case,
    good_test_files,
)


@pytest.mark.parametrize(
    "test_case",
    [
        FftConfiguredLayoutTestCase(
            description="qa mirrors a python runtime package",
            roots=("python/mypkg",),
            tests=("qa",),
            tooling=(),
            source_path="python/mypkg/domain/__init__.py",
            test_path="qa/unit/python/mypkg/domain/test_example.py",
            expected_codes=(),
        ),
        FftConfiguredLayoutTestCase(
            description="qa mirrors nested tooling",
            roots=("python/mypkg",),
            tests=("qa",),
            tooling=("dev/tools",),
            source_path="dev/tools/release/__init__.py",
            test_path="qa/unit/dev/tools/release/test_example.py",
            expected_codes=(),
        ),
    ],
    ids=lambda case: case.description,
)
def test_given_configured_layout_when_checking_all_layout_rules_then_accepts_exact_mirror(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    test_case: FftConfiguredLayoutTestCase,
) -> None:
    result: EvaluationResult = evaluate_configured_layout_test_case(
        test_case=test_case,
        tmp_path=tmp_path,
        monkeypatch=monkeypatch,
    )

    assert tuple(fault.code for fault in result.faults) == test_case.expected_codes


@pytest.mark.parametrize(
    "test_case",
    [
        FftOperationTestCase(
            description="complete native tests family uses prewarmed project observations",
            expected_parse_count=0,
            expected_layout_count=0,
            expected_function_issue_count=0,
        )
    ],
    ids=lambda case: case.description,
)
def test_given_complete_tests_family_when_evaluating_then_bounds_local_type_loading(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    test_case: FftOperationTestCase,
) -> None:
    test_types_path: Path = tmp_path / "tests/unit/src/fensu/rules/tests/main/_test_types.py"
    test_module_path: Path = tmp_path / "tests/unit/src/fensu/rules/tests/main/test_example.py"
    runtime_path: Path = tmp_path / "src/fensu/rules/__init__.py"
    for path, source in (
        (test_types_path, GOOD_TEST_TYPES_SOURCE),
        (test_module_path, GOOD_TEST_SOURCE),
        (runtime_path, ""),
    ):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(source, encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    config: Config = Config(roots=("src/fensu",), tests=("tests",))
    parse_counts: list[int] = [0]
    layout_counts: list[int] = [0]
    function_issue_counts: list[int] = [0]
    original_layout_issue: Callable[..., test_checks._LayoutIssue | None] = (
        test_checks._layout_issue
    )
    original_function_issues: Callable[..., dict[FftCode, tuple[SourceLocation, ...]]] = (
        test_checks._test_function_issue_locations
    )

    def count_parse(scoped_file: ScopedFile) -> ParsedModule:
        parse_counts[0] += 1
        return parse_scoped_file(scoped_file=scoped_file)

    def count_layout_issue(*, ctx: RuleContext) -> test_checks._LayoutIssue | None:
        layout_counts[0] += 1
        return original_layout_issue(ctx=ctx)

    def count_function_issues(
        *,
        ctx: RuleContext,
        module_context: test_checks._TestModuleContext,
    ) -> dict[FftCode, tuple[SourceLocation, ...]]:
        function_issue_counts[0] += 1
        return original_function_issues(ctx=ctx, module_context=module_context)

    monkeypatch.setattr(
        "fensu.evaluation._helpers.project_analysis.parse_scoped_file",
        count_parse,
    )
    monkeypatch.setattr(test_checks, "_layout_issue", count_layout_issue)
    monkeypatch.setattr(
        test_checks,
        "_test_function_issue_locations",
        count_function_issues,
    )

    _result: EvaluationResult = evaluate(
        tree=discover_files(config=config), ruleset=FFT_RULES, config=config
    )

    assert parse_counts[0] == test_case.expected_parse_count
    assert layout_counts[0] == test_case.expected_layout_count
    assert function_issue_counts[0] == test_case.expected_function_issue_count


@pytest.mark.parametrize(
    "test_case",
    [
        FftRuleTestCase(
            description="bad test scope is flagged",
            rule_code="FFT002",
            files=(
                FftRuleFile(
                    description="bad scope test",
                    relative_path="tests/slow/src/fensu/rules/tests/main/test_example.py",
                    source=GOOD_TEST_SOURCE,
                ),
            ),
            expected_codes=("FFT002",),
            expected_lines=(None,),
        ),
        FftRuleTestCase(
            description="missing mirrored src area is flagged",
            rule_code="FFT006",
            files=(
                FftRuleFile(
                    description="missing area test",
                    relative_path="tests/unit/src/fensu/missing/test_example.py",
                    source=GOOD_TEST_SOURCE,
                ),
            ),
            expected_codes=("FFT006",),
            expected_lines=(None,),
            runtime_paths=("src/fensu/__init__.py",),
        ),
        FftRuleTestCase(
            description="mirrored src area is allowed",
            rule_code="FFT006",
            files=good_test_files(),
            expected_codes=(),
            expected_lines=(),
            runtime_paths=("src/fensu/rules/__init__.py",),
        ),
        FftRuleTestCase(
            description="custom test root mirrors a python source root",
            rule_code="FFT006",
            files=(
                FftRuleFile(
                    description="configured source mirror",
                    relative_path="qa/unit/python/mypkg/domain/test_example.py",
                    source=GOOD_TEST_SOURCE,
                ),
            ),
            expected_codes=(),
            expected_lines=(),
            runtime_paths=("python/mypkg/domain/__init__.py",),
            roots=("python/mypkg",),
            tests=("qa",),
            tooling=(),
        ),
        FftRuleTestCase(
            description="reserved root area under runtime package is allowed",
            rule_code="FFT006",
            files=(
                FftRuleFile(
                    description="package root test",
                    relative_path="tests/unit/src/fensu/__root__/test_surface.py",
                    source=GOOD_TEST_SOURCE,
                ),
            ),
            expected_codes=(),
            expected_lines=(),
            runtime_paths=("src/fensu/__init__.py",),
        ),
        FftRuleTestCase(
            description="reserved root area under an unconfigured package is rejected",
            rule_code="FFT005",
            files=(
                FftRuleFile(
                    description="foreign package root test",
                    relative_path="tests/unit/src/other/__root__/test_surface.py",
                    source=GOOD_TEST_SOURCE,
                ),
            ),
            expected_codes=("FFT005",),
            expected_lines=(None,),
            runtime_paths=("src/other/__init__.py",),
        ),
        FftRuleTestCase(
            description="bad mirrored root is flagged",
            rule_code="FFT003",
            files=(
                FftRuleFile(
                    description="bad mirrored root test",
                    relative_path="tests/unit/docs/fensu/test_example.py",
                    source=GOOD_TEST_SOURCE,
                ),
            ),
            expected_codes=("FFT003",),
            expected_lines=(None,),
        ),
        FftRuleTestCase(
            description="shallow src mirror is flagged",
            rule_code="FFT004",
            files=(
                FftRuleFile(
                    description="shallow src test",
                    relative_path="tests/unit/src/test_example.py",
                    source=GOOD_TEST_SOURCE,
                ),
            ),
            expected_codes=("FFT004",),
            expected_lines=(None,),
        ),
        FftRuleTestCase(
            description="missing src package is flagged",
            rule_code="FFT005",
            files=(
                FftRuleFile(
                    description="missing package test",
                    relative_path="tests/unit/src/unknown/core/test_example.py",
                    source=GOOD_TEST_SOURCE,
                ),
            ),
            expected_codes=("FFT005",),
            expected_lines=(None,),
        ),
        FftRuleTestCase(
            description="shallow scripts mirror is flagged",
            rule_code="FFT007",
            files=(
                FftRuleFile(
                    description="shallow scripts test",
                    relative_path="tests/unit/scripts/test_example.py",
                    source=GOOD_TEST_SOURCE,
                ),
            ),
            expected_codes=("FFT007",),
            expected_lines=(None,),
        ),
        FftRuleTestCase(
            description="missing scripts area is flagged",
            rule_code="FFT008",
            files=(
                FftRuleFile(
                    description="missing scripts test",
                    relative_path="tests/unit/scripts/missing/test_example.py",
                    source=GOOD_TEST_SOURCE,
                ),
            ),
            expected_codes=("FFT008",),
            expected_lines=(None,),
        ),
        FftRuleTestCase(
            description="custom test root mirrors nested configured tooling",
            rule_code="FFT008",
            files=(
                FftRuleFile(
                    description="configured tooling mirror",
                    relative_path="qa/unit/dev/tools/release/test_example.py",
                    source=GOOD_TEST_SOURCE,
                ),
            ),
            expected_codes=(),
            expected_lines=(),
            tooling_paths=("dev/tools/release/__init__.py",),
            tests=("qa",),
            tooling=("dev/tools",),
        ),
        FftRuleTestCase(
            description="test scope infrastructure is exempt from mirrored layout",
            rule_code="FFT001",
            files=(
                FftRuleFile(
                    description="scope conftest",
                    relative_path="tests/unit/conftest.py",
                    source="",
                ),
            ),
            expected_codes=(),
            expected_lines=(),
        ),
    ],
    ids=lambda case: case.description,
)
def test_given_test_layout_when_checking_tests_then_flags_only_bad_mirroring(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    test_case: FftRuleTestCase,
) -> None:
    result: EvaluationResult = evaluate_tests_rule_test_case(
        test_case=test_case, tmp_path=tmp_path, monkeypatch=monkeypatch
    )

    assert tuple(fault.code for fault in result.faults) == test_case.expected_codes
    assert tuple(fault.line for fault in result.faults) == test_case.expected_lines


@pytest.mark.parametrize(
    "test_case",
    [
        FftRuleTestCase(
            description="nonempty init module is flagged",
            rule_code="FFT101",
            files=(
                FftRuleFile(
                    description="bad init",
                    relative_path="tests/unit/src/fensu/rules/tests/main/__init__.py",
                    source="value: int = 1\n",
                ),
            ),
            expected_codes=("FFT101",),
            expected_lines=(None,),
            runtime_paths=("src/fensu/rules/__init__.py",),
        ),
        FftRuleTestCase(
            description="relative import is flagged",
            rule_code="FFT102",
            files=good_test_files(test_source="from .helpers import value\n"),
            expected_codes=("FFT102",),
            expected_lines=(1,),
            runtime_paths=("src/fensu/rules/__init__.py",),
        ),
        FftRuleTestCase(
            description="top-level helper function is flagged",
            rule_code="FFT103",
            files=good_test_files(
                test_source=f"{GOOD_TEST_SOURCE}\n\ndef helper() -> None:\n    return None\n"
            ),
            expected_codes=("FFT103",),
            expected_lines=(14,),
            runtime_paths=("src/fensu/rules/__init__.py",),
        ),
        FftRuleTestCase(
            description="unused module test case list is not independently flagged",
            rule_code="FFT408",
            files=good_test_files(test_source=f"TEST_CASES = []\n{GOOD_TEST_SOURCE}"),
            expected_codes=(),
            expected_lines=(),
            runtime_paths=("src/fensu/rules/__init__.py",),
        ),
        FftRuleTestCase(
            description="private constant after test is flagged",
            rule_code="FFT105",
            files=good_test_files(test_source=f"{GOOD_TEST_SOURCE}\n_PRIVATE: int = 1\n"),
            expected_codes=("FFT105",),
            expected_lines=(13,),
            runtime_paths=("src/fensu/rules/__init__.py",),
        ),
        FftRuleTestCase(
            description="test support helpers may define top-level functions",
            rule_code="FFT103",
            files=(
                FftRuleFile(
                    description="local helpers",
                    relative_path="tests/unit/src/fensu/rules/tests/main/helpers.py",
                    source="def build_case() -> object:\n    return object()\n",
                ),
            ),
            expected_codes=(),
            expected_lines=(),
            runtime_paths=("src/fensu/rules/__init__.py",),
        ),
        FftRuleTestCase(
            description="test module without local test types file is flagged",
            rule_code="FFT204",
            files=(
                FftRuleFile(
                    description="test without types",
                    relative_path="tests/unit/src/fensu/rules/main/test_example.py",
                    source=GOOD_TEST_SOURCE,
                ),
            ),
            expected_codes=("FFT204",),
            expected_lines=(None,),
            runtime_paths=("src/fensu/rules/__init__.py",),
        ),
        FftRuleTestCase(
            description="test module with local test types file is allowed",
            rule_code="FFT204",
            files=good_test_files(),
            expected_codes=(),
            expected_lines=(),
            runtime_paths=("src/fensu/rules/__init__.py",),
        ),
        FftRuleTestCase(
            description="legacy test helper support module is not a test file",
            rule_code="FFT301",
            files=(
                FftRuleFile(
                    description="legacy local helpers",
                    relative_path="tests/unit/src/fensu/rules/tests/main/_test_helpers.py",
                    source="",
                ),
            ),
            expected_codes=(),
            expected_lines=(),
            runtime_paths=("src/fensu/rules/__init__.py",),
        ),
    ],
    ids=lambda case: case.description,
)
def test_given_test_modules_when_checking_hygiene_then_flags_only_module_violations(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    test_case: FftRuleTestCase,
) -> None:
    result: EvaluationResult = evaluate_tests_rule_test_case(
        test_case=test_case, tmp_path=tmp_path, monkeypatch=monkeypatch
    )

    assert tuple(fault.code for fault in result.faults) == test_case.expected_codes
    assert tuple(fault.line for fault in result.faults) == test_case.expected_lines


@pytest.mark.parametrize(
    "test_case",
    [
        FftRuleTestCase(
            description="test type missing description is flagged",
            rule_code="FFT201",
            files=(
                FftRuleFile(
                    description="bad test types",
                    relative_path="tests/unit/src/fensu/rules/tests/main/_test_types.py",
                    source="from dataclasses import dataclass\n\n@dataclass(frozen=True)\nclass ExampleTestCase:\n    expected_value: int\n",
                ),
            ),
            expected_codes=("FFT201",),
            expected_lines=(4,),
            runtime_paths=("src/fensu/rules/__init__.py",),
        ),
        FftRuleTestCase(
            description="test type missing expected field is flagged",
            rule_code="FFT202",
            files=(
                FftRuleFile(
                    description="bad test types",
                    relative_path="tests/unit/src/fensu/rules/tests/main/_test_types.py",
                    source="from dataclasses import dataclass\n\n@dataclass(frozen=True)\nclass ExampleTestCase:\n    description: str\n",
                ),
            ),
            expected_codes=("FFT202",),
            expected_lines=(4,),
            runtime_paths=("src/fensu/rules/__init__.py",),
        ),
        FftRuleTestCase(
            description="foreign test types import is flagged",
            rule_code="FFT203",
            files=good_test_files(
                test_source="from tests.unit.src.fensu.rules.other._test_types import ExampleTestCase\n"
            ),
            expected_codes=("FFT203",),
            expected_lines=(1,),
            runtime_paths=("src/fensu/rules/__init__.py",),
        ),
        FftRuleTestCase(
            description="scenario models non dataclass is flagged",
            rule_code="FFT001",
            files=(
                FftRuleFile(
                    description="scenario models",
                    relative_path="tests/unit/src/fensu/rules/tests/main/scenario_models.py",
                    source="class Result:\n    value: int\n",
                ),
            ),
            expected_codes=("FFT001",),
            expected_lines=(1,),
            runtime_paths=("src/fensu/rules/__init__.py",),
        ),
    ],
    ids=lambda case: case.description,
)
def test_given_test_types_when_checking_tests_then_flags_only_type_role_violations(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    test_case: FftRuleTestCase,
) -> None:
    result: EvaluationResult = evaluate_tests_rule_test_case(
        test_case=test_case, tmp_path=tmp_path, monkeypatch=monkeypatch
    )

    assert tuple(fault.code for fault in result.faults) == test_case.expected_codes
    assert tuple(fault.line for fault in result.faults) == test_case.expected_lines


@pytest.mark.parametrize(
    "test_case",
    [
        FftRuleTestCase(
            description="bad test file name is flagged",
            rule_code="FFT301",
            files=(
                FftRuleFile(
                    description="types",
                    relative_path="tests/unit/src/fensu/rules/tests/main/_test_types.py",
                    source=GOOD_TEST_TYPES_SOURCE,
                ),
                FftRuleFile(
                    description="bad name",
                    relative_path="tests/unit/src/fensu/rules/tests/main/example.py",
                    source=GOOD_TEST_SOURCE,
                ),
            ),
            expected_codes=("FFT301",),
            expected_lines=(None,),
            runtime_paths=("src/fensu/rules/__init__.py",),
        ),
        FftRuleTestCase(
            description="bad test function name is flagged",
            rule_code="FFT302",
            files=good_test_files(
                test_source=GOOD_TEST_SOURCE.replace(
                    "test_given_value_when_checking_then_matches_expected", "test_bad_name"
                )
            ),
            expected_codes=("FFT302",),
            expected_lines=(10,),
            runtime_paths=("src/fensu/rules/__init__.py",),
        ),
        FftRuleTestCase(
            description="if statement in test is flagged",
            rule_code="FFT104",
            files=good_test_files(
                test_source=GOOD_TEST_SOURCE.replace("    assert", "    if True:\n        assert")
            ),
            expected_codes=("FFT104",),
            expected_lines=(11,),
            runtime_paths=("src/fensu/rules/__init__.py",),
        ),
        FftRuleTestCase(
            description="ternary expression in test is flagged",
            rule_code="FFT104",
            files=good_test_files(
                test_source=GOOD_TEST_SOURCE.replace(
                    "    assert",
                    "    result: int = 1 if test_case.expected_value else 0\n    assert",
                )
            ),
            expected_codes=("FFT104",),
            expected_lines=(11,),
            runtime_paths=("src/fensu/rules/__init__.py",),
        ),
        FftRuleTestCase(
            description="match statement in test is flagged",
            rule_code="FFT104",
            files=good_test_files(
                test_source=GOOD_TEST_SOURCE.replace(
                    "    assert",
                    "    match test_case.expected_value:\n        case 1:\n            pass\n    assert",
                )
            ),
            expected_codes=("FFT104",),
            expected_lines=(11,),
            runtime_paths=("src/fensu/rules/__init__.py",),
        ),
        FftRuleTestCase(
            description="while statement in test is allowed",
            rule_code="FFT104",
            files=good_test_files(
                test_source=GOOD_TEST_SOURCE.replace(
                    "    assert",
                    "    while test_case.expected_value < 0:\n        break\n    assert",
                )
            ),
            expected_codes=(),
            expected_lines=(),
            runtime_paths=("src/fensu/rules/__init__.py",),
        ),
        FftRuleTestCase(
            description="filtered comprehension in test is flagged",
            rule_code="FFT104",
            files=good_test_files(
                test_source=GOOD_TEST_SOURCE.replace(
                    "    assert",
                    "    values: list[int] = [value for value in (1, 2) if value > 1]\n    assert",
                )
            ),
            expected_codes=("FFT104",),
            expected_lines=(11,),
            runtime_paths=("src/fensu/rules/__init__.py",),
        ),
        FftRuleTestCase(
            description="single unfiltered comprehension in test is allowed",
            rule_code="FFT104",
            files=good_test_files(
                test_source=GOOD_TEST_SOURCE.replace(
                    "    assert",
                    "    values: list[int] = [value for value in (1, 2)]\n    assert",
                )
            ),
            expected_codes=(),
            expected_lines=(),
            runtime_paths=("src/fensu/rules/__init__.py",),
        ),
        FftRuleTestCase(
            description="conditional expression in parametrize cases is outside the test body",
            rule_code="FFT104",
            files=good_test_files(
                test_source=GOOD_TEST_SOURCE.replace(
                    "expected_value=1", "expected_value=(1 if True else 0)"
                )
            ),
            expected_codes=(),
            expected_lines=(),
            runtime_paths=("src/fensu/rules/__init__.py",),
        ),
        FftRuleTestCase(
            description="wrong test case annotation is flagged",
            rule_code="FFT403",
            files=good_test_files(
                test_source=GOOD_TEST_SOURCE.replace(
                    "test_case: ExampleTestCase", "test_case: object"
                )
            ),
            expected_codes=("FFT403",),
            expected_lines=(10,),
            runtime_paths=("src/fensu/rules/__init__.py",),
        ),
    ],
    ids=lambda case: case.description,
)
def test_given_test_functions_when_checking_shape_then_flags_only_function_violations(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    test_case: FftRuleTestCase,
) -> None:
    result: EvaluationResult = evaluate_tests_rule_test_case(
        test_case=test_case, tmp_path=tmp_path, monkeypatch=monkeypatch
    )

    assert tuple(fault.code for fault in result.faults) == test_case.expected_codes
    assert tuple(fault.line for fault in result.faults) == test_case.expected_lines


@pytest.mark.parametrize(
    "test_case",
    [
        FftRuleTestCase(
            description="nonparametrized sync test condition is flagged",
            rule_code="FFT104",
            files=good_test_files(
                test_source=(
                    "def test_given_value_when_checking_then_matches_expected() -> None:\n"
                    "    if True:\n"
                    "        assert True\n"
                )
            ),
            expected_codes=("FFT104",),
            expected_lines=(2,),
            runtime_paths=("src/fensu/rules/__init__.py",),
        ),
        FftRuleTestCase(
            description="nonparametrized async test conditional expression is flagged",
            rule_code="FFT104",
            files=good_test_files(
                test_source=(
                    "async def test_given_value_when_checking_then_matches_expected() -> None:\n"
                    "    result: int = 1 if True else 0\n"
                    "    assert result == 1\n"
                )
            ),
            expected_codes=("FFT104",),
            expected_lines=(2,),
            runtime_paths=("src/fensu/rules/__init__.py",),
        ),
        FftRuleTestCase(
            description="helper sync async and class definitions use identical conditional semantics",
            rule_code="FFT104",
            files=(
                *good_test_files(),
                FftRuleFile(
                    description="local helpers",
                    relative_path="tests/unit/src/fensu/rules/tests/main/helpers.py",
                    source=(
                        "def choose() -> None:\n"
                        "    if True:\n"
                        "        pass\n\n"
                        "async def choose_async() -> None:\n"
                        "    match 1:\n"
                        "        case 1:\n"
                        "            pass\n\n"
                        "class Chooser:\n"
                        "    selected: int = 1 if True else 0\n"
                        "    values: list[int] = [value for value in (1, 2) if value]\n"
                    ),
                ),
            ),
            expected_codes=("FFT104", "FFT104", "FFT104", "FFT104"),
            expected_lines=(2, 6, 11, 12),
            runtime_paths=("src/fensu/rules/__init__.py",),
        ),
        FftRuleTestCase(
            description="underscore test helper module definitions are checked",
            rule_code="FFT104",
            files=(
                *good_test_files(),
                FftRuleFile(
                    description="alternate local helpers",
                    relative_path="tests/unit/src/fensu/rules/tests/main/_test_helpers.py",
                    source="def choose() -> int:\n    return 1 if True else 0\n",
                ),
            ),
            expected_codes=("FFT104",),
            expected_lines=(2,),
            runtime_paths=("src/fensu/rules/__init__.py",),
        ),
        FftRuleTestCase(
            description="module level conditions outside definitions are allowed",
            rule_code="FFT104",
            files=(
                *good_test_files(),
                FftRuleFile(
                    description="local helpers",
                    relative_path="tests/unit/src/fensu/rules/tests/main/helpers.py",
                    source=("if True:\n    VALUE: int = 1\nSELECTED: int = 1 if True else 0\n"),
                ),
            ),
            expected_codes=(),
            expected_lines=(),
            runtime_paths=("src/fensu/rules/__init__.py",),
        ),
        FftRuleTestCase(
            description="while and try remain allowed in tests and helpers",
            rule_code="FFT104",
            files=(
                *good_test_files(
                    test_source=(
                        "def test_given_value_when_checking_then_matches_expected() -> None:\n"
                        "    while False:\n"
                        "        pass\n"
                        "    try:\n"
                        "        assert True\n"
                        "    except ValueError:\n"
                        "        pass\n"
                    )
                ),
                FftRuleFile(
                    description="local helpers",
                    relative_path="tests/unit/src/fensu/rules/tests/main/helpers.py",
                    source=(
                        "def wait() -> None:\n"
                        "    while False:\n"
                        "        pass\n"
                        "    try:\n"
                        "        pass\n"
                        "    except ValueError:\n"
                        "        pass\n"
                    ),
                ),
            ),
            expected_codes=(),
            expected_lines=(),
            runtime_paths=("src/fensu/rules/__init__.py",),
        ),
        FftRuleTestCase(
            description="complex filtered comprehension belongs only to FFT106",
            rule_code="FFT104,FFT106",
            files=(
                *good_test_files(),
                FftRuleFile(
                    description="local helpers",
                    relative_path="tests/unit/src/fensu/rules/tests/main/helpers.py",
                    source=(
                        "def pairs() -> list[tuple[int, int]]:\n"
                        "    return [(left, right) for left in (1, 2) for right in (3, 4) if right]\n"
                    ),
                ),
            ),
            expected_codes=("FFT106",),
            expected_lines=(2,),
            runtime_paths=("src/fensu/rules/__init__.py",),
        ),
    ],
    ids=lambda case: case.description,
)
def test_given_extended_conditional_contract_when_checking_then_reports_owned_constructs_once(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    test_case: FftRuleTestCase,
) -> None:
    result: EvaluationResult = evaluate_tests_rule_test_case(
        test_case=test_case, tmp_path=tmp_path, monkeypatch=monkeypatch
    )

    assert tuple(fault.code for fault in result.faults) == test_case.expected_codes
    assert tuple(fault.line for fault in result.faults) == test_case.expected_lines


@pytest.mark.parametrize(
    "test_case",
    [
        FftRuleTestCase(
            description="test comprehension with two generators is flagged",
            rule_code="FFT106",
            files=good_test_files(
                test_source=GOOD_TEST_SOURCE.replace(
                    "    assert",
                    "    pairs: list[tuple[int, int]] = [(left, right) for left in (1, 2) for right in (3, 4)]\n    assert",
                )
            ),
            expected_codes=("FFT106",),
            expected_lines=(11,),
            runtime_paths=("src/fensu/rules/__init__.py",),
        ),
        FftRuleTestCase(
            description="test comprehension containing another comprehension is flagged",
            rule_code="FFT106",
            files=good_test_files(
                test_source=GOOD_TEST_SOURCE.replace(
                    "    assert",
                    "    rows: list[list[int]] = [[value for value in row] for row in ((1, 2),)]\n    assert",
                )
            ),
            expected_codes=("FFT106",),
            expected_lines=(11,),
            runtime_paths=("src/fensu/rules/__init__.py",),
        ),
        FftRuleTestCase(
            description="single filtered test comprehension is simple shape",
            rule_code="FFT106",
            files=good_test_files(
                test_source=GOOD_TEST_SOURCE.replace(
                    "    assert",
                    "    values: list[int] = [value for value in (1, 2) if value > 1]\n    assert",
                )
            ),
            expected_codes=(),
            expected_lines=(),
            runtime_paths=("src/fensu/rules/__init__.py",),
        ),
    ],
    ids=lambda case: case.description,
)
def test_given_test_comprehensions_when_checking_then_flags_only_complex_forms(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    test_case: FftRuleTestCase,
) -> None:
    result: EvaluationResult = evaluate_tests_rule_test_case(
        test_case=test_case, tmp_path=tmp_path, monkeypatch=monkeypatch
    )

    assert tuple(fault.code for fault in result.faults) == test_case.expected_codes
    assert tuple(fault.line for fault in result.faults) == test_case.expected_lines


@pytest.mark.parametrize(
    "test_case",
    [
        FftRuleTestCase(
            description="all newly native local FFT rules bypass Python core callbacks",
            rule_code=(
                "FFT001,FFT002,FFT003,FFT004,FFT005,FFT006,FFT007,FFT008,FFT101,FFT103,"
                "FFT104,FFT105,FFT201,FFT202,FFT203,FFT204,FFT301,FFT302,FFT401,FFT402,"
                "FFT403,FFT404,FFT405,FFT406,FFT407,FFT408,FFT411,FFT412,FFT413,FFT414"
            ),
            files=good_test_files(),
            expected_codes=(),
            expected_lines=(),
            runtime_paths=("src/fensu/rules/__init__.py",),
        ),
        FftRuleTestCase(
            description="native FFT102 bypasses its Python core callback",
            rule_code="FFT102",
            files=good_test_files(test_source="from .helpers import build_case\n"),
            expected_codes=("FFT102",),
            expected_lines=(1,),
            runtime_paths=("src/fensu/rules/__init__.py",),
        ),
        FftRuleTestCase(
            description="native FFT106 bypasses its Python core callback",
            rule_code="FFT106",
            files=good_test_files(
                test_source=("pairs = [(left, right) for left in (1, 2) for right in (3, 4)]\n")
            ),
            expected_codes=("FFT106",),
            expected_lines=(1,),
            runtime_paths=("src/fensu/rules/__init__.py",),
        ),
    ],
    ids=lambda case: case.description,
)
def test_given_registered_native_test_rule_when_evaluating_then_skips_python_callback(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    test_case: FftRuleTestCase,
) -> None:
    python_callback: Mock = Mock(side_effect=AssertionError("Python callback executed"))
    monkeypatch.setattr(testing_rules_module, "test_faults", python_callback)

    result: EvaluationResult = evaluate_tests_rule_test_case(
        test_case=test_case, tmp_path=tmp_path, monkeypatch=monkeypatch
    )

    assert tuple(fault.code for fault in result.faults) == test_case.expected_codes
    assert python_callback.call_count == 0


@pytest.mark.parametrize(
    "test_case",
    [
        FftRuleTestCase(
            description="missing parametrize is flagged",
            rule_code="FFT401",
            files=good_test_files(
                test_source="def test_given_value_when_checking_then_matches_expected() -> None:\n    assert True\n"
            ),
            expected_codes=("FFT401",),
            expected_lines=(1,),
            runtime_paths=("src/fensu/rules/__init__.py",),
        ),
        FftRuleTestCase(
            description="missing test_case argument is flagged",
            rule_code="FFT402",
            files=good_test_files(
                test_source=GOOD_TEST_SOURCE.replace(
                    "test_case: ExampleTestCase", "case: ExampleTestCase"
                )
            ),
            expected_codes=("FFT402",),
            expected_lines=(10,),
            runtime_paths=("src/fensu/rules/__init__.py",),
        ),
        FftRuleTestCase(
            description="missing expected field assertion is flagged",
            rule_code="FFT404",
            files=good_test_files(
                test_source=GOOD_TEST_SOURCE.replace("test_case.expected_value", "1")
            ),
            expected_codes=("FFT404",),
            expected_lines=(10,),
            runtime_paths=("src/fensu/rules/__init__.py",),
        ),
        FftRuleTestCase(
            description="dict literal test case is flagged",
            rule_code="FFT412",
            files=good_test_files(
                test_source=GOOD_TEST_SOURCE.replace(
                    'ExampleTestCase(description="example", expected_value=1)',
                    "{'description': 'example'}",
                )
            ),
            expected_codes=("FFT412",),
            expected_lines=(7,),
            runtime_paths=("src/fensu/rules/__init__.py",),
        ),
        FftRuleTestCase(
            description="missing ids lambda is flagged",
            rule_code="FFT414",
            files=good_test_files(
                test_source=GOOD_TEST_SOURCE.replace(
                    "ids=lambda case: case.description", "ids=['example']"
                )
            ),
            expected_codes=("FFT414",),
            expected_lines=(10,),
            runtime_paths=("src/fensu/rules/__init__.py",),
        ),
        FftRuleTestCase(
            description="parametrize missing values is flagged",
            rule_code="FFT405",
            files=good_test_files(
                test_source=GOOD_TEST_SOURCE.replace(
                    '    [ExampleTestCase(description="example", expected_value=1)],\n', ""
                )
            ),
            expected_codes=("FFT405",),
            expected_lines=(9,),
            runtime_paths=("src/fensu/rules/__init__.py",),
        ),
        FftRuleTestCase(
            description="wrong parametrized argument is flagged",
            rule_code="FFT406",
            files=good_test_files(test_source=GOOD_TEST_SOURCE.replace('"test_case"', '"case"')),
            expected_codes=("FFT406",),
            expected_lines=(10,),
            runtime_paths=("src/fensu/rules/__init__.py",),
        ),
        FftRuleTestCase(
            description="missing parametrized ids is flagged",
            rule_code="FFT407",
            files=good_test_files(
                test_source=GOOD_TEST_SOURCE.replace("    ids=lambda case: case.description,\n", "")
            ),
            expected_codes=("FFT407",),
            expected_lines=(9,),
            runtime_paths=("src/fensu/rules/__init__.py",),
        ),
        FftRuleTestCase(
            description="named parametrized values are flagged",
            rule_code="FFT408",
            files=good_test_files(
                test_source=f"CASES = [ExampleTestCase(description='example', expected_value=1)]\n{GOOD_TEST_SOURCE.replace('[ExampleTestCase(description="example", expected_value=1)]', 'CASES')}"
            ),
            expected_codes=("FFT408",),
            expected_lines=(11,),
            runtime_paths=("src/fensu/rules/__init__.py",),
        ),
        FftRuleTestCase(
            description="opaque call parametrized values are flagged",
            rule_code="FFT408",
            files=good_test_files(
                test_source=GOOD_TEST_SOURCE.replace(
                    '[ExampleTestCase(description="example", expected_value=1)]', "make_cases()"
                )
            ),
            expected_codes=("FFT408",),
            expected_lines=(10,),
            runtime_paths=("src/fensu/rules/__init__.py",),
        ),
        FftRuleTestCase(
            description="opaque attribute expression parametrized values are flagged",
            rule_code="FFT408",
            files=good_test_files(
                test_source=GOOD_TEST_SOURCE.replace(
                    '[ExampleTestCase(description="example", expected_value=1)]', "cases.values"
                )
            ),
            expected_codes=("FFT408",),
            expected_lines=(10,),
            runtime_paths=("src/fensu/rules/__init__.py",),
        ),
        FftRuleTestCase(
            description="inline tuple parametrized values are visible",
            rule_code="FFT408",
            files=good_test_files(
                test_source=GOOD_TEST_SOURCE.replace(
                    '[ExampleTestCase(description="example", expected_value=1)]',
                    '(ExampleTestCase(description="example", expected_value=1),)',
                )
            ),
            expected_codes=(),
            expected_lines=(),
            runtime_paths=("src/fensu/rules/__init__.py",),
        ),
        FftRuleTestCase(
            description="inline generator comprehension parametrized values are visible",
            rule_code="FFT408",
            files=good_test_files(
                test_source=GOOD_TEST_SOURCE.replace(
                    '[ExampleTestCase(description="example", expected_value=1)]',
                    "(ExampleTestCase(description=str(value), expected_value=value) for value in (1, 2))",
                )
            ),
            expected_codes=(),
            expected_lines=(),
            runtime_paths=("src/fensu/rules/__init__.py",),
        ),
        FftRuleTestCase(
            description="full ruleset reports named values once at the parametrized function",
            rule_code="FF",
            files=good_test_files(
                test_source=(
                    "CASES: list[ExampleTestCase] = "
                    "[ExampleTestCase(description='example', expected_value=1)]\n"
                    f"{GOOD_TEST_SOURCE.replace('[ExampleTestCase(description="example", expected_value=1)]', 'CASES')}"
                )
            ),
            expected_codes=("FFT408",),
            expected_lines=(11,),
            runtime_paths=(
                "src/fensu/rules/core/constants.py",
                "src/fensu/rules/core/main/_run.py",
            ),
        ),
        FftRuleTestCase(
            description="empty parametrized values are flagged",
            rule_code="FFT411",
            files=good_test_files(
                test_source=GOOD_TEST_SOURCE.replace(
                    '[ExampleTestCase(description="example", expected_value=1)]', "[]"
                )
            ),
            expected_codes=("FFT411",),
            expected_lines=(10,),
            runtime_paths=("src/fensu/rules/__init__.py",),
        ),
        FftRuleTestCase(
            description="non local constructor is flagged",
            rule_code="FFT413",
            files=good_test_files(
                test_source=GOOD_TEST_SOURCE.replace("ExampleTestCase(", "object(")
            ),
            expected_codes=("FFT413",),
            expected_lines=(7,),
            runtime_paths=("src/fensu/rules/__init__.py",),
        ),
        FftRuleTestCase(
            description="local test case constructor is allowed",
            rule_code="FFT413",
            files=good_test_files(),
            expected_codes=(),
            expected_lines=(),
            runtime_paths=("src/fensu/rules/__init__.py",),
        ),
        FftRuleTestCase(
            description="generated local test case matrix is allowed",
            rule_code="FFT413",
            files=good_test_files(
                test_source=GOOD_TEST_SOURCE.replace(
                    '[ExampleTestCase(description="example", expected_value=1)]',
                    '[ExampleTestCase(description=f"{value}", expected_value=value) for value in (1, 2)]',
                )
            ),
            expected_codes=(),
            expected_lines=(),
            runtime_paths=("src/fensu/rules/__init__.py",),
        ),
    ],
    ids=lambda case: case.description,
)
def test_given_parametrized_tests_when_checking_tests_then_flags_parametrize_violations(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    test_case: FftRuleTestCase,
) -> None:
    result: EvaluationResult = evaluate_tests_rule_test_case(
        test_case=test_case, tmp_path=tmp_path, monkeypatch=monkeypatch
    )

    assert tuple(fault.code for fault in result.faults) == test_case.expected_codes
    assert tuple(fault.line for fault in result.faults) == test_case.expected_lines
