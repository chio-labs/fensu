"""Tests for tests-family rules."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

import pytest

from strata.config.models import Config
from strata.discovery.main.discover_files import discover_files
from strata.discovery.models import ScopedFile
from strata.evaluation.helpers.parsing import parse_scoped_file
from strata.evaluation.main.evaluate import evaluate
from strata.evaluation.models import EvaluationResult, ParsedModule
from strata.rules.authoring.types import RuleContext
from strata.rules.tests.constants import SFT_RULES
from strata.rules.tests.helpers import checks as test_checks
from tests.unit.src.strata.rules.tests.main._test_types import (
    SftConfiguredLayoutTestCase,
    SftOperationTestCase,
    SftRuleFile,
    SftRuleTestCase,
)
from tests.unit.src.strata.rules.tests.main.helpers import (
    GOOD_TEST_SOURCE,
    GOOD_TEST_TYPES_SOURCE,
    evaluate_configured_layout_test_case,
    evaluate_tests_rule_test_case,
    good_test_files,
)


@pytest.mark.parametrize(
    "test_case",
    [
        SftConfiguredLayoutTestCase(
            description="qa mirrors a python runtime package",
            roots=("python/mypkg",),
            tests=("qa",),
            tooling=(),
            source_path="python/mypkg/domain/__init__.py",
            test_path="qa/unit/python/mypkg/domain/test_example.py",
            expected_codes=(),
        ),
        SftConfiguredLayoutTestCase(
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
    test_case: SftConfiguredLayoutTestCase,
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
        SftOperationTestCase(
            description="complete tests family parses each discovered file only once",
            expected_parse_count=3,
            expected_layout_count=2,
        )
    ],
    ids=lambda case: case.description,
)
def test_given_complete_tests_family_when_evaluating_then_bounds_local_type_loading(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    test_case: SftOperationTestCase,
) -> None:
    test_types_path: Path = tmp_path / "tests/unit/src/strata/rules/tests/main/_test_types.py"
    test_module_path: Path = tmp_path / "tests/unit/src/strata/rules/tests/main/test_example.py"
    runtime_path: Path = tmp_path / "src/strata/rules/__init__.py"
    for path, source in (
        (test_types_path, GOOD_TEST_TYPES_SOURCE),
        (test_module_path, GOOD_TEST_SOURCE),
        (runtime_path, ""),
    ):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(source, encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    config: Config = Config(roots=("src/strata",), tests=("tests",))
    parse_counts: list[int] = [0]
    layout_counts: list[int] = [0]
    original_layout_issue: Callable[..., test_checks._LayoutIssue | None] = (
        test_checks._layout_issue
    )

    def count_parse(scoped_file: ScopedFile) -> ParsedModule:
        parse_counts[0] += 1
        return parse_scoped_file(scoped_file=scoped_file)

    def count_layout_issue(*, ctx: RuleContext) -> test_checks._LayoutIssue | None:
        layout_counts[0] += 1
        return original_layout_issue(ctx=ctx)

    monkeypatch.setattr(
        "strata.evaluation.helpers.project_analysis.parse_scoped_file",
        count_parse,
    )
    monkeypatch.setattr(test_checks, "_layout_issue", count_layout_issue)

    _result: EvaluationResult = evaluate(
        tree=discover_files(config=config), ruleset=SFT_RULES, config=config
    )

    assert parse_counts[0] == test_case.expected_parse_count
    assert layout_counts[0] == test_case.expected_layout_count


@pytest.mark.parametrize(
    "test_case",
    [
        SftRuleTestCase(
            description="bad test scope is flagged",
            rule_code="SFT002",
            files=(
                SftRuleFile(
                    description="bad scope test",
                    relative_path="tests/slow/src/strata/rules/tests/main/test_example.py",
                    source=GOOD_TEST_SOURCE,
                ),
            ),
            expected_codes=("SFT002",),
            expected_lines=(None,),
        ),
        SftRuleTestCase(
            description="missing mirrored src area is flagged",
            rule_code="SFT006",
            files=(
                SftRuleFile(
                    description="missing area test",
                    relative_path="tests/unit/src/strata/missing/test_example.py",
                    source=GOOD_TEST_SOURCE,
                ),
            ),
            expected_codes=("SFT006",),
            expected_lines=(None,),
            runtime_paths=("src/strata/__init__.py",),
        ),
        SftRuleTestCase(
            description="mirrored src area is allowed",
            rule_code="SFT006",
            files=good_test_files(),
            expected_codes=(),
            expected_lines=(),
            runtime_paths=("src/strata/rules/__init__.py",),
        ),
        SftRuleTestCase(
            description="custom test root mirrors a python source root",
            rule_code="SFT006",
            files=(
                SftRuleFile(
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
        SftRuleTestCase(
            description="reserved root area under runtime package is allowed",
            rule_code="SFT006",
            files=(
                SftRuleFile(
                    description="package root test",
                    relative_path="tests/unit/src/strata/__root__/test_surface.py",
                    source=GOOD_TEST_SOURCE,
                ),
            ),
            expected_codes=(),
            expected_lines=(),
            runtime_paths=("src/strata/__init__.py",),
        ),
        SftRuleTestCase(
            description="reserved root area under an unconfigured package is rejected",
            rule_code="SFT005",
            files=(
                SftRuleFile(
                    description="foreign package root test",
                    relative_path="tests/unit/src/other/__root__/test_surface.py",
                    source=GOOD_TEST_SOURCE,
                ),
            ),
            expected_codes=("SFT005",),
            expected_lines=(None,),
            runtime_paths=("src/other/__init__.py",),
        ),
        SftRuleTestCase(
            description="bad mirrored root is flagged",
            rule_code="SFT003",
            files=(
                SftRuleFile(
                    description="bad mirrored root test",
                    relative_path="tests/unit/docs/strata/test_example.py",
                    source=GOOD_TEST_SOURCE,
                ),
            ),
            expected_codes=("SFT003",),
            expected_lines=(None,),
        ),
        SftRuleTestCase(
            description="shallow src mirror is flagged",
            rule_code="SFT004",
            files=(
                SftRuleFile(
                    description="shallow src test",
                    relative_path="tests/unit/src/test_example.py",
                    source=GOOD_TEST_SOURCE,
                ),
            ),
            expected_codes=("SFT004",),
            expected_lines=(None,),
        ),
        SftRuleTestCase(
            description="missing src package is flagged",
            rule_code="SFT005",
            files=(
                SftRuleFile(
                    description="missing package test",
                    relative_path="tests/unit/src/unknown/core/test_example.py",
                    source=GOOD_TEST_SOURCE,
                ),
            ),
            expected_codes=("SFT005",),
            expected_lines=(None,),
        ),
        SftRuleTestCase(
            description="shallow scripts mirror is flagged",
            rule_code="SFT007",
            files=(
                SftRuleFile(
                    description="shallow scripts test",
                    relative_path="tests/unit/scripts/test_example.py",
                    source=GOOD_TEST_SOURCE,
                ),
            ),
            expected_codes=("SFT007",),
            expected_lines=(None,),
        ),
        SftRuleTestCase(
            description="missing scripts area is flagged",
            rule_code="SFT008",
            files=(
                SftRuleFile(
                    description="missing scripts test",
                    relative_path="tests/unit/scripts/missing/test_example.py",
                    source=GOOD_TEST_SOURCE,
                ),
            ),
            expected_codes=("SFT008",),
            expected_lines=(None,),
        ),
        SftRuleTestCase(
            description="custom test root mirrors nested configured tooling",
            rule_code="SFT008",
            files=(
                SftRuleFile(
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
        SftRuleTestCase(
            description="test scope infrastructure is exempt from mirrored layout",
            rule_code="SFT001",
            files=(
                SftRuleFile(
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
    test_case: SftRuleTestCase,
) -> None:
    result: EvaluationResult = evaluate_tests_rule_test_case(
        test_case=test_case, tmp_path=tmp_path, monkeypatch=monkeypatch
    )

    assert tuple(fault.code for fault in result.faults) == test_case.expected_codes
    assert tuple(fault.line for fault in result.faults) == test_case.expected_lines


@pytest.mark.parametrize(
    "test_case",
    [
        SftRuleTestCase(
            description="nonempty init module is flagged",
            rule_code="SFT101",
            files=(
                SftRuleFile(
                    description="bad init",
                    relative_path="tests/unit/src/strata/rules/tests/main/__init__.py",
                    source="value: int = 1\n",
                ),
            ),
            expected_codes=("SFT101",),
            expected_lines=(None,),
            runtime_paths=("src/strata/rules/__init__.py",),
        ),
        SftRuleTestCase(
            description="relative import is flagged",
            rule_code="SFT102",
            files=good_test_files(test_source="from .helpers import value\n"),
            expected_codes=("SFT102",),
            expected_lines=(1,),
            runtime_paths=("src/strata/rules/__init__.py",),
        ),
        SftRuleTestCase(
            description="top-level helper function is flagged",
            rule_code="SFT103",
            files=good_test_files(
                test_source=f"{GOOD_TEST_SOURCE}\n\ndef helper() -> None:\n    return None\n"
            ),
            expected_codes=("SFT103",),
            expected_lines=(14,),
            runtime_paths=("src/strata/rules/__init__.py",),
        ),
        SftRuleTestCase(
            description="module test case list is flagged",
            rule_code="SFT408",
            files=good_test_files(test_source=f"TEST_CASES = []\n{GOOD_TEST_SOURCE}"),
            expected_codes=("SFT408",),
            expected_lines=(1,),
            runtime_paths=("src/strata/rules/__init__.py",),
        ),
        SftRuleTestCase(
            description="private constant after test is flagged",
            rule_code="SFT105",
            files=good_test_files(test_source=f"{GOOD_TEST_SOURCE}\n_PRIVATE: int = 1\n"),
            expected_codes=("SFT105",),
            expected_lines=(13,),
            runtime_paths=("src/strata/rules/__init__.py",),
        ),
        SftRuleTestCase(
            description="test support helpers may define top-level functions",
            rule_code="SFT103",
            files=(
                SftRuleFile(
                    description="local helpers",
                    relative_path="tests/unit/src/strata/rules/tests/main/helpers.py",
                    source="def build_case() -> object:\n    return object()\n",
                ),
            ),
            expected_codes=(),
            expected_lines=(),
            runtime_paths=("src/strata/rules/__init__.py",),
        ),
        SftRuleTestCase(
            description="test module without local test types file is flagged",
            rule_code="SFT204",
            files=(
                SftRuleFile(
                    description="test without types",
                    relative_path="tests/unit/src/strata/rules/main/test_example.py",
                    source=GOOD_TEST_SOURCE,
                ),
            ),
            expected_codes=("SFT204",),
            expected_lines=(None,),
            runtime_paths=("src/strata/rules/__init__.py",),
        ),
        SftRuleTestCase(
            description="test module with local test types file is allowed",
            rule_code="SFT204",
            files=good_test_files(),
            expected_codes=(),
            expected_lines=(),
            runtime_paths=("src/strata/rules/__init__.py",),
        ),
        SftRuleTestCase(
            description="legacy test helper support module is not a test file",
            rule_code="SFT301",
            files=(
                SftRuleFile(
                    description="legacy local helpers",
                    relative_path="tests/unit/src/strata/rules/tests/main/_test_helpers.py",
                    source="",
                ),
            ),
            expected_codes=(),
            expected_lines=(),
            runtime_paths=("src/strata/rules/__init__.py",),
        ),
    ],
    ids=lambda case: case.description,
)
def test_given_test_modules_when_checking_hygiene_then_flags_only_module_violations(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    test_case: SftRuleTestCase,
) -> None:
    result: EvaluationResult = evaluate_tests_rule_test_case(
        test_case=test_case, tmp_path=tmp_path, monkeypatch=monkeypatch
    )

    assert tuple(fault.code for fault in result.faults) == test_case.expected_codes
    assert tuple(fault.line for fault in result.faults) == test_case.expected_lines


@pytest.mark.parametrize(
    "test_case",
    [
        SftRuleTestCase(
            description="test type missing description is flagged",
            rule_code="SFT201",
            files=(
                SftRuleFile(
                    description="bad test types",
                    relative_path="tests/unit/src/strata/rules/tests/main/_test_types.py",
                    source="from dataclasses import dataclass\n\n@dataclass(frozen=True)\nclass ExampleTestCase:\n    expected_value: int\n",
                ),
            ),
            expected_codes=("SFT201",),
            expected_lines=(4,),
            runtime_paths=("src/strata/rules/__init__.py",),
        ),
        SftRuleTestCase(
            description="test type missing expected field is flagged",
            rule_code="SFT202",
            files=(
                SftRuleFile(
                    description="bad test types",
                    relative_path="tests/unit/src/strata/rules/tests/main/_test_types.py",
                    source="from dataclasses import dataclass\n\n@dataclass(frozen=True)\nclass ExampleTestCase:\n    description: str\n",
                ),
            ),
            expected_codes=("SFT202",),
            expected_lines=(4,),
            runtime_paths=("src/strata/rules/__init__.py",),
        ),
        SftRuleTestCase(
            description="foreign test types import is flagged",
            rule_code="SFT203",
            files=good_test_files(
                test_source="from tests.unit.src.strata.rules.other._test_types import ExampleTestCase\n"
            ),
            expected_codes=("SFT203",),
            expected_lines=(1,),
            runtime_paths=("src/strata/rules/__init__.py",),
        ),
        SftRuleTestCase(
            description="scenario models non dataclass is flagged",
            rule_code="SFT001",
            files=(
                SftRuleFile(
                    description="scenario models",
                    relative_path="tests/unit/src/strata/rules/tests/main/scenario_models.py",
                    source="class Result:\n    value: int\n",
                ),
            ),
            expected_codes=("SFT001",),
            expected_lines=(1,),
            runtime_paths=("src/strata/rules/__init__.py",),
        ),
    ],
    ids=lambda case: case.description,
)
def test_given_test_types_when_checking_tests_then_flags_only_type_role_violations(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    test_case: SftRuleTestCase,
) -> None:
    result: EvaluationResult = evaluate_tests_rule_test_case(
        test_case=test_case, tmp_path=tmp_path, monkeypatch=monkeypatch
    )

    assert tuple(fault.code for fault in result.faults) == test_case.expected_codes
    assert tuple(fault.line for fault in result.faults) == test_case.expected_lines


@pytest.mark.parametrize(
    "test_case",
    [
        SftRuleTestCase(
            description="bad test file name is flagged",
            rule_code="SFT301",
            files=(
                SftRuleFile(
                    description="types",
                    relative_path="tests/unit/src/strata/rules/tests/main/_test_types.py",
                    source=GOOD_TEST_TYPES_SOURCE,
                ),
                SftRuleFile(
                    description="bad name",
                    relative_path="tests/unit/src/strata/rules/tests/main/example.py",
                    source=GOOD_TEST_SOURCE,
                ),
            ),
            expected_codes=("SFT301",),
            expected_lines=(None,),
            runtime_paths=("src/strata/rules/__init__.py",),
        ),
        SftRuleTestCase(
            description="bad test function name is flagged",
            rule_code="SFT302",
            files=good_test_files(
                test_source=GOOD_TEST_SOURCE.replace(
                    "test_given_value_when_checking_then_matches_expected", "test_bad_name"
                )
            ),
            expected_codes=("SFT302",),
            expected_lines=(10,),
            runtime_paths=("src/strata/rules/__init__.py",),
        ),
        SftRuleTestCase(
            description="if statement in test is flagged",
            rule_code="SFT104",
            files=good_test_files(
                test_source=GOOD_TEST_SOURCE.replace("    assert", "    if True:\n        assert")
            ),
            expected_codes=("SFT104",),
            expected_lines=(11,),
            runtime_paths=("src/strata/rules/__init__.py",),
        ),
        SftRuleTestCase(
            description="ternary expression in test is flagged",
            rule_code="SFT104",
            files=good_test_files(
                test_source=GOOD_TEST_SOURCE.replace(
                    "    assert",
                    "    result: int = 1 if test_case.expected_value else 0\n    assert",
                )
            ),
            expected_codes=("SFT104",),
            expected_lines=(11,),
            runtime_paths=("src/strata/rules/__init__.py",),
        ),
        SftRuleTestCase(
            description="match statement in test is flagged",
            rule_code="SFT104",
            files=good_test_files(
                test_source=GOOD_TEST_SOURCE.replace(
                    "    assert",
                    "    match test_case.expected_value:\n        case 1:\n            pass\n    assert",
                )
            ),
            expected_codes=("SFT104",),
            expected_lines=(11,),
            runtime_paths=("src/strata/rules/__init__.py",),
        ),
        SftRuleTestCase(
            description="while statement in test is flagged",
            rule_code="SFT104",
            files=good_test_files(
                test_source=GOOD_TEST_SOURCE.replace(
                    "    assert",
                    "    while test_case.expected_value < 0:\n        break\n    assert",
                )
            ),
            expected_codes=("SFT104",),
            expected_lines=(11,),
            runtime_paths=("src/strata/rules/__init__.py",),
        ),
        SftRuleTestCase(
            description="filtered comprehension in test is flagged",
            rule_code="SFT104",
            files=good_test_files(
                test_source=GOOD_TEST_SOURCE.replace(
                    "    assert",
                    "    values: list[int] = [value for value in (1, 2) if value > 1]\n    assert",
                )
            ),
            expected_codes=("SFT104",),
            expected_lines=(11,),
            runtime_paths=("src/strata/rules/__init__.py",),
        ),
        SftRuleTestCase(
            description="single unfiltered comprehension in test is allowed",
            rule_code="SFT104",
            files=good_test_files(
                test_source=GOOD_TEST_SOURCE.replace(
                    "    assert",
                    "    values: list[int] = [value for value in (1, 2)]\n    assert",
                )
            ),
            expected_codes=(),
            expected_lines=(),
            runtime_paths=("src/strata/rules/__init__.py",),
        ),
        SftRuleTestCase(
            description="conditional expression in parametrize cases is outside the test body",
            rule_code="SFT104",
            files=good_test_files(
                test_source=GOOD_TEST_SOURCE.replace(
                    "expected_value=1", "expected_value=(1 if True else 0)"
                )
            ),
            expected_codes=(),
            expected_lines=(),
            runtime_paths=("src/strata/rules/__init__.py",),
        ),
        SftRuleTestCase(
            description="wrong test case annotation is flagged",
            rule_code="SFT403",
            files=good_test_files(
                test_source=GOOD_TEST_SOURCE.replace(
                    "test_case: ExampleTestCase", "test_case: object"
                )
            ),
            expected_codes=("SFT403",),
            expected_lines=(10,),
            runtime_paths=("src/strata/rules/__init__.py",),
        ),
    ],
    ids=lambda case: case.description,
)
def test_given_test_functions_when_checking_shape_then_flags_only_function_violations(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    test_case: SftRuleTestCase,
) -> None:
    result: EvaluationResult = evaluate_tests_rule_test_case(
        test_case=test_case, tmp_path=tmp_path, monkeypatch=monkeypatch
    )

    assert tuple(fault.code for fault in result.faults) == test_case.expected_codes
    assert tuple(fault.line for fault in result.faults) == test_case.expected_lines


@pytest.mark.parametrize(
    "test_case",
    [
        SftRuleTestCase(
            description="test comprehension with two generators is flagged",
            rule_code="SFT106",
            files=good_test_files(
                test_source=GOOD_TEST_SOURCE.replace(
                    "    assert",
                    "    pairs: list[tuple[int, int]] = [(left, right) for left in (1, 2) for right in (3, 4)]\n    assert",
                )
            ),
            expected_codes=("SFT106",),
            expected_lines=(11,),
            runtime_paths=("src/strata/rules/__init__.py",),
        ),
        SftRuleTestCase(
            description="test comprehension containing another comprehension is flagged",
            rule_code="SFT106",
            files=good_test_files(
                test_source=GOOD_TEST_SOURCE.replace(
                    "    assert",
                    "    rows: list[list[int]] = [[value for value in row] for row in ((1, 2),)]\n    assert",
                )
            ),
            expected_codes=("SFT106",),
            expected_lines=(11,),
            runtime_paths=("src/strata/rules/__init__.py",),
        ),
        SftRuleTestCase(
            description="single filtered test comprehension is simple shape",
            rule_code="SFT106",
            files=good_test_files(
                test_source=GOOD_TEST_SOURCE.replace(
                    "    assert",
                    "    values: list[int] = [value for value in (1, 2) if value > 1]\n    assert",
                )
            ),
            expected_codes=(),
            expected_lines=(),
            runtime_paths=("src/strata/rules/__init__.py",),
        ),
    ],
    ids=lambda case: case.description,
)
def test_given_test_comprehensions_when_checking_then_flags_only_complex_forms(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    test_case: SftRuleTestCase,
) -> None:
    result: EvaluationResult = evaluate_tests_rule_test_case(
        test_case=test_case, tmp_path=tmp_path, monkeypatch=monkeypatch
    )

    assert tuple(fault.code for fault in result.faults) == test_case.expected_codes
    assert tuple(fault.line for fault in result.faults) == test_case.expected_lines


@pytest.mark.parametrize(
    "test_case",
    [
        SftRuleTestCase(
            description="missing parametrize is flagged",
            rule_code="SFT401",
            files=good_test_files(
                test_source="def test_given_value_when_checking_then_matches_expected() -> None:\n    assert True\n"
            ),
            expected_codes=("SFT401",),
            expected_lines=(1,),
            runtime_paths=("src/strata/rules/__init__.py",),
        ),
        SftRuleTestCase(
            description="missing test_case argument is flagged",
            rule_code="SFT402",
            files=good_test_files(
                test_source=GOOD_TEST_SOURCE.replace(
                    "test_case: ExampleTestCase", "case: ExampleTestCase"
                )
            ),
            expected_codes=("SFT402",),
            expected_lines=(10,),
            runtime_paths=("src/strata/rules/__init__.py",),
        ),
        SftRuleTestCase(
            description="missing expected field assertion is flagged",
            rule_code="SFT404",
            files=good_test_files(
                test_source=GOOD_TEST_SOURCE.replace("test_case.expected_value", "1")
            ),
            expected_codes=("SFT404",),
            expected_lines=(10,),
            runtime_paths=("src/strata/rules/__init__.py",),
        ),
        SftRuleTestCase(
            description="dict literal test case is flagged",
            rule_code="SFT412",
            files=good_test_files(
                test_source=GOOD_TEST_SOURCE.replace(
                    'ExampleTestCase(description="example", expected_value=1)',
                    "{'description': 'example'}",
                )
            ),
            expected_codes=("SFT412",),
            expected_lines=(7,),
            runtime_paths=("src/strata/rules/__init__.py",),
        ),
        SftRuleTestCase(
            description="missing ids lambda is flagged",
            rule_code="SFT414",
            files=good_test_files(
                test_source=GOOD_TEST_SOURCE.replace(
                    "ids=lambda case: case.description", "ids=['example']"
                )
            ),
            expected_codes=("SFT414",),
            expected_lines=(10,),
            runtime_paths=("src/strata/rules/__init__.py",),
        ),
        SftRuleTestCase(
            description="parametrize missing values is flagged",
            rule_code="SFT405",
            files=good_test_files(
                test_source=GOOD_TEST_SOURCE.replace(
                    '    [ExampleTestCase(description="example", expected_value=1)],\n', ""
                )
            ),
            expected_codes=("SFT405",),
            expected_lines=(9,),
            runtime_paths=("src/strata/rules/__init__.py",),
        ),
        SftRuleTestCase(
            description="wrong parametrized argument is flagged",
            rule_code="SFT406",
            files=good_test_files(test_source=GOOD_TEST_SOURCE.replace('"test_case"', '"case"')),
            expected_codes=("SFT406",),
            expected_lines=(10,),
            runtime_paths=("src/strata/rules/__init__.py",),
        ),
        SftRuleTestCase(
            description="missing parametrized ids is flagged",
            rule_code="SFT407",
            files=good_test_files(
                test_source=GOOD_TEST_SOURCE.replace("    ids=lambda case: case.description,\n", "")
            ),
            expected_codes=("SFT407",),
            expected_lines=(9,),
            runtime_paths=("src/strata/rules/__init__.py",),
        ),
        SftRuleTestCase(
            description="named parametrized values are flagged",
            rule_code="SFT409",
            files=good_test_files(
                test_source=f"CASES = [ExampleTestCase(description='example', expected_value=1)]\n{GOOD_TEST_SOURCE.replace('[ExampleTestCase(description="example", expected_value=1)]', 'CASES')}"
            ),
            expected_codes=("SFT409",),
            expected_lines=(11,),
            runtime_paths=("src/strata/rules/__init__.py",),
        ),
        SftRuleTestCase(
            description="non sequence parametrized values are flagged",
            rule_code="SFT410",
            files=good_test_files(
                test_source=GOOD_TEST_SOURCE.replace(
                    '[ExampleTestCase(description="example", expected_value=1)]', "make_cases()"
                )
            ),
            expected_codes=("SFT410",),
            expected_lines=(10,),
            runtime_paths=("src/strata/rules/__init__.py",),
        ),
        SftRuleTestCase(
            description="empty parametrized values are flagged",
            rule_code="SFT411",
            files=good_test_files(
                test_source=GOOD_TEST_SOURCE.replace(
                    '[ExampleTestCase(description="example", expected_value=1)]', "[]"
                )
            ),
            expected_codes=("SFT411",),
            expected_lines=(10,),
            runtime_paths=("src/strata/rules/__init__.py",),
        ),
        SftRuleTestCase(
            description="non local constructor is flagged",
            rule_code="SFT413",
            files=good_test_files(
                test_source=GOOD_TEST_SOURCE.replace("ExampleTestCase(", "object(")
            ),
            expected_codes=("SFT413",),
            expected_lines=(7,),
            runtime_paths=("src/strata/rules/__init__.py",),
        ),
        SftRuleTestCase(
            description="local test case constructor is allowed",
            rule_code="SFT413",
            files=good_test_files(),
            expected_codes=(),
            expected_lines=(),
            runtime_paths=("src/strata/rules/__init__.py",),
        ),
        SftRuleTestCase(
            description="generated local test case matrix is allowed",
            rule_code="SFT413",
            files=good_test_files(
                test_source=GOOD_TEST_SOURCE.replace(
                    '[ExampleTestCase(description="example", expected_value=1)]',
                    '[ExampleTestCase(description=f"{value}", expected_value=value) for value in (1, 2)]',
                )
            ),
            expected_codes=(),
            expected_lines=(),
            runtime_paths=("src/strata/rules/__init__.py",),
        ),
    ],
    ids=lambda case: case.description,
)
def test_given_parametrized_tests_when_checking_tests_then_flags_parametrize_violations(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    test_case: SftRuleTestCase,
) -> None:
    result: EvaluationResult = evaluate_tests_rule_test_case(
        test_case=test_case, tmp_path=tmp_path, monkeypatch=monkeypatch
    )

    assert tuple(fault.code for fault in result.faults) == test_case.expected_codes
    assert tuple(fault.line for fault in result.faults) == test_case.expected_lines
