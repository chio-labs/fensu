"""Tests for tests-family rules."""

from __future__ import annotations

from pathlib import Path

import pytest

from strata.evaluation.core.models import EvaluationResult
from tests.unit.src.strata.rules.tests.main._test_types import SftRuleFile, SftRuleTestCase
from tests.unit.src.strata.rules.tests.main.helpers import (
    GOOD_TEST_SOURCE,
    GOOD_TEST_TYPES_SOURCE,
    evaluate_tests_rule_test_case,
    good_test_files,
)


@pytest.mark.parametrize(
    "test_case",
    [
        SftRuleTestCase(
            description="bad test scope is flagged",
            rule_code="SFT029",
            files=(
                SftRuleFile(
                    description="bad scope test",
                    relative_path="tests/slow/src/strata/rules/tests/main/test_example.py",
                    source=GOOD_TEST_SOURCE,
                ),
            ),
            expected_codes=("SFT029",),
            expected_lines=(None,),
        ),
        SftRuleTestCase(
            description="missing mirrored src area is flagged",
            rule_code="SFT033",
            files=(
                SftRuleFile(
                    description="missing area test",
                    relative_path="tests/unit/src/strata/missing/test_example.py",
                    source=GOOD_TEST_SOURCE,
                ),
            ),
            expected_codes=("SFT033",),
            expected_lines=(None,),
            runtime_paths=("src/strata/__init__.py",),
        ),
        SftRuleTestCase(
            description="mirrored src area is allowed",
            rule_code="SFT033",
            files=good_test_files(),
            expected_codes=(),
            expected_lines=(),
            runtime_paths=("src/strata/rules/__init__.py",),
        ),
        SftRuleTestCase(
            description="bad mirrored root is flagged",
            rule_code="SFT030",
            files=(
                SftRuleFile(
                    description="bad mirrored root test",
                    relative_path="tests/unit/docs/strata/test_example.py",
                    source=GOOD_TEST_SOURCE,
                ),
            ),
            expected_codes=("SFT030",),
            expected_lines=(None,),
        ),
        SftRuleTestCase(
            description="shallow src mirror is flagged",
            rule_code="SFT031",
            files=(
                SftRuleFile(
                    description="shallow src test",
                    relative_path="tests/unit/src/test_example.py",
                    source=GOOD_TEST_SOURCE,
                ),
            ),
            expected_codes=("SFT031",),
            expected_lines=(None,),
        ),
        SftRuleTestCase(
            description="missing src package is flagged",
            rule_code="SFT032",
            files=(
                SftRuleFile(
                    description="missing package test",
                    relative_path="tests/unit/src/unknown/core/test_example.py",
                    source=GOOD_TEST_SOURCE,
                ),
            ),
            expected_codes=("SFT032",),
            expected_lines=(None,),
        ),
        SftRuleTestCase(
            description="shallow scripts mirror is flagged",
            rule_code="SFT034",
            files=(
                SftRuleFile(
                    description="shallow scripts test",
                    relative_path="tests/unit/scripts/test_example.py",
                    source=GOOD_TEST_SOURCE,
                ),
            ),
            expected_codes=("SFT034",),
            expected_lines=(None,),
        ),
        SftRuleTestCase(
            description="missing scripts area is flagged",
            rule_code="SFT035",
            files=(
                SftRuleFile(
                    description="missing scripts test",
                    relative_path="tests/unit/scripts/missing/test_example.py",
                    source=GOOD_TEST_SOURCE,
                ),
            ),
            expected_codes=("SFT035",),
            expected_lines=(None,),
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
            rule_code="SFT001",
            files=(
                SftRuleFile(
                    description="bad init",
                    relative_path="tests/unit/src/strata/rules/tests/main/__init__.py",
                    source="value: int = 1\n",
                ),
            ),
            expected_codes=("SFT001",),
            expected_lines=(None,),
            runtime_paths=("src/strata/rules/__init__.py",),
        ),
        SftRuleTestCase(
            description="relative import is flagged",
            rule_code="SFT002",
            files=good_test_files(test_source="from .helpers import value\n"),
            expected_codes=("SFT002",),
            expected_lines=(1,),
            runtime_paths=("src/strata/rules/__init__.py",),
        ),
        SftRuleTestCase(
            description="top-level helper function is flagged",
            rule_code="SFT027",
            files=good_test_files(
                test_source=f"{GOOD_TEST_SOURCE}\n\ndef helper() -> None:\n    return None\n"
            ),
            expected_codes=("SFT027",),
            expected_lines=(14,),
            runtime_paths=("src/strata/rules/__init__.py",),
        ),
        SftRuleTestCase(
            description="module test case list is flagged",
            rule_code="SFT015",
            files=good_test_files(test_source=f"TEST_CASES = []\n{GOOD_TEST_SOURCE}"),
            expected_codes=("SFT015",),
            expected_lines=(1,),
            runtime_paths=("src/strata/rules/__init__.py",),
        ),
        SftRuleTestCase(
            description="private constant after test is flagged",
            rule_code="SFT037",
            files=good_test_files(test_source=f"{GOOD_TEST_SOURCE}\n_PRIVATE: int = 1\n"),
            expected_codes=("SFT037",),
            expected_lines=(13,),
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
            rule_code="SFT003",
            files=(
                SftRuleFile(
                    description="bad test types",
                    relative_path="tests/unit/src/strata/rules/tests/main/_test_types.py",
                    source="from dataclasses import dataclass\n\n@dataclass(frozen=True)\nclass ExampleTestCase:\n    expected_value: int\n",
                ),
            ),
            expected_codes=("SFT003",),
            expected_lines=(4,),
            runtime_paths=("src/strata/rules/__init__.py",),
        ),
        SftRuleTestCase(
            description="test type missing expected field is flagged",
            rule_code="SFT004",
            files=(
                SftRuleFile(
                    description="bad test types",
                    relative_path="tests/unit/src/strata/rules/tests/main/_test_types.py",
                    source="from dataclasses import dataclass\n\n@dataclass(frozen=True)\nclass ExampleTestCase:\n    description: str\n",
                ),
            ),
            expected_codes=("SFT004",),
            expected_lines=(4,),
            runtime_paths=("src/strata/rules/__init__.py",),
        ),
        SftRuleTestCase(
            description="foreign test types import is flagged",
            rule_code="SFT005",
            files=good_test_files(
                test_source="from tests.unit.src.strata.rules.other._test_types import ExampleTestCase\n"
            ),
            expected_codes=("SFT005",),
            expected_lines=(1,),
            runtime_paths=("src/strata/rules/__init__.py",),
        ),
        SftRuleTestCase(
            description="scenario models non dataclass is flagged",
            rule_code="SFT028",
            files=(
                SftRuleFile(
                    description="scenario models",
                    relative_path="tests/unit/src/strata/rules/tests/main/scenario_models.py",
                    source="class Result:\n    value: int\n",
                ),
            ),
            expected_codes=("SFT028",),
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
            rule_code="SFT006",
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
            expected_codes=("SFT006",),
            expected_lines=(None,),
            runtime_paths=("src/strata/rules/__init__.py",),
        ),
        SftRuleTestCase(
            description="bad test function name is flagged",
            rule_code="SFT007",
            files=good_test_files(
                test_source=GOOD_TEST_SOURCE.replace(
                    "test_given_value_when_checking_then_matches_expected", "test_bad_name"
                )
            ),
            expected_codes=("SFT007",),
            expected_lines=(10,),
            runtime_paths=("src/strata/rules/__init__.py",),
        ),
        SftRuleTestCase(
            description="if statement in test is flagged",
            rule_code="SFT036",
            files=good_test_files(
                test_source=GOOD_TEST_SOURCE.replace("    assert", "    if True:\n        assert")
            ),
            expected_codes=("SFT036",),
            expected_lines=(11,),
            runtime_paths=("src/strata/rules/__init__.py",),
        ),
        SftRuleTestCase(
            description="wrong test case annotation is flagged",
            rule_code="SFT010",
            files=good_test_files(
                test_source=GOOD_TEST_SOURCE.replace(
                    "test_case: ExampleTestCase", "test_case: object"
                )
            ),
            expected_codes=("SFT010",),
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
            description="missing parametrize is flagged",
            rule_code="SFT008",
            files=good_test_files(
                test_source="def test_given_value_when_checking_then_matches_expected() -> None:\n    assert True\n"
            ),
            expected_codes=("SFT008",),
            expected_lines=(1,),
            runtime_paths=("src/strata/rules/__init__.py",),
        ),
        SftRuleTestCase(
            description="missing test_case argument is flagged",
            rule_code="SFT009",
            files=good_test_files(
                test_source=GOOD_TEST_SOURCE.replace(
                    "test_case: ExampleTestCase", "case: ExampleTestCase"
                )
            ),
            expected_codes=("SFT009",),
            expected_lines=(10,),
            runtime_paths=("src/strata/rules/__init__.py",),
        ),
        SftRuleTestCase(
            description="missing expected field assertion is flagged",
            rule_code="SFT011",
            files=good_test_files(
                test_source=GOOD_TEST_SOURCE.replace("test_case.expected_value", "1")
            ),
            expected_codes=("SFT011",),
            expected_lines=(10,),
            runtime_paths=("src/strata/rules/__init__.py",),
        ),
        SftRuleTestCase(
            description="dict literal test case is flagged",
            rule_code="SFT023",
            files=good_test_files(
                test_source=GOOD_TEST_SOURCE.replace(
                    'ExampleTestCase(description="example", expected_value=1)',
                    "{'description': 'example'}",
                )
            ),
            expected_codes=("SFT023",),
            expected_lines=(7,),
            runtime_paths=("src/strata/rules/__init__.py",),
        ),
        SftRuleTestCase(
            description="missing ids lambda is flagged",
            rule_code="SFT025",
            files=good_test_files(
                test_source=GOOD_TEST_SOURCE.replace(
                    "ids=lambda case: case.description", "ids=['example']"
                )
            ),
            expected_codes=("SFT025",),
            expected_lines=(10,),
            runtime_paths=("src/strata/rules/__init__.py",),
        ),
        SftRuleTestCase(
            description="parametrize missing values is flagged",
            rule_code="SFT012",
            files=good_test_files(
                test_source=GOOD_TEST_SOURCE.replace(
                    '    [ExampleTestCase(description="example", expected_value=1)],\n', ""
                )
            ),
            expected_codes=("SFT012",),
            expected_lines=(9,),
            runtime_paths=("src/strata/rules/__init__.py",),
        ),
        SftRuleTestCase(
            description="wrong parametrized argument is flagged",
            rule_code="SFT013",
            files=good_test_files(test_source=GOOD_TEST_SOURCE.replace('"test_case"', '"case"')),
            expected_codes=("SFT013",),
            expected_lines=(10,),
            runtime_paths=("src/strata/rules/__init__.py",),
        ),
        SftRuleTestCase(
            description="missing parametrized ids is flagged",
            rule_code="SFT014",
            files=good_test_files(
                test_source=GOOD_TEST_SOURCE.replace("    ids=lambda case: case.description,\n", "")
            ),
            expected_codes=("SFT014",),
            expected_lines=(9,),
            runtime_paths=("src/strata/rules/__init__.py",),
        ),
        SftRuleTestCase(
            description="named parametrized values are flagged",
            rule_code="SFT016",
            files=good_test_files(
                test_source=f"CASES = [ExampleTestCase(description='example', expected_value=1)]\n{GOOD_TEST_SOURCE.replace('[ExampleTestCase(description="example", expected_value=1)]', 'CASES')}"
            ),
            expected_codes=("SFT016",),
            expected_lines=(11,),
            runtime_paths=("src/strata/rules/__init__.py",),
        ),
        SftRuleTestCase(
            description="non sequence parametrized values are flagged",
            rule_code="SFT021",
            files=good_test_files(
                test_source=GOOD_TEST_SOURCE.replace(
                    '[ExampleTestCase(description="example", expected_value=1)]', "make_cases()"
                )
            ),
            expected_codes=("SFT021",),
            expected_lines=(10,),
            runtime_paths=("src/strata/rules/__init__.py",),
        ),
        SftRuleTestCase(
            description="empty parametrized values are flagged",
            rule_code="SFT022",
            files=good_test_files(
                test_source=GOOD_TEST_SOURCE.replace(
                    '[ExampleTestCase(description="example", expected_value=1)]', "[]"
                )
            ),
            expected_codes=("SFT022",),
            expected_lines=(10,),
            runtime_paths=("src/strata/rules/__init__.py",),
        ),
        SftRuleTestCase(
            description="non local constructor is flagged",
            rule_code="SFT024",
            files=good_test_files(
                test_source=GOOD_TEST_SOURCE.replace("ExampleTestCase(", "object(")
            ),
            expected_codes=("SFT024",),
            expected_lines=(7,),
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
