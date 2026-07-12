"""Tests for annotation rules."""

from __future__ import annotations

from pathlib import Path

import pytest

from strata.evaluation.models import EvaluationResult
from tests.unit.src.strata.rules.annotations.main._test_types import AnnotationRuleTestCase
from tests.unit.src.strata.rules.annotations.main.helpers import evaluate_annotation_test_case


@pytest.mark.parametrize(
    "test_case",
    [
        AnnotationRuleTestCase(
            description="unannotated parameter is flagged",
            rule_code="SFA001",
            source="def run(value) -> None:\n    return None\n",
            expected_codes=("SFA001",),
            expected_lines=(1,),
        ),
        AnnotationRuleTestCase(
            description="method self parameter is exempt",
            rule_code="SFA001",
            source="class Service:\n    def run(self, value: int) -> None:\n        return None\n",
            expected_codes=(),
            expected_lines=(),
        ),
        AnnotationRuleTestCase(
            description="unannotated vararg and kwarg are flagged",
            rule_code="SFA001",
            source="def run(*items, **kwargs) -> None:\n    return None\n",
            expected_codes=("SFA001", "SFA001"),
            expected_lines=(1, 1),
        ),
        AnnotationRuleTestCase(
            description="async unannotated parameter is flagged",
            rule_code="SFA001",
            source="async def run(value) -> None:\n    return None\n",
            expected_codes=("SFA001",),
            expected_lines=(1,),
        ),
    ],
    ids=lambda case: case.description,
)
def test_given_parameters_when_checking_annotations_then_flags_only_unannotated_parameters(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    test_case: AnnotationRuleTestCase,
) -> None:
    result: EvaluationResult = evaluate_annotation_test_case(
        test_case=test_case, tmp_path=tmp_path, monkeypatch=monkeypatch
    )

    assert tuple(fault.code for fault in result.faults) == test_case.expected_codes
    assert tuple(fault.line for fault in result.faults) == test_case.expected_lines


@pytest.mark.parametrize(
    "test_case",
    [
        AnnotationRuleTestCase(
            description="missing return annotation is flagged",
            rule_code="SFA002",
            source="def run(value: int):\n    return None\n",
            expected_codes=("SFA002",),
            expected_lines=(1,),
        ),
        AnnotationRuleTestCase(
            description="return annotation is allowed",
            rule_code="SFA002",
            source="def run(value: int) -> None:\n    return None\n",
            expected_codes=(),
            expected_lines=(),
        ),
        AnnotationRuleTestCase(
            description="async missing return annotation is flagged",
            rule_code="SFA002",
            source="async def run(value: int):\n    return None\n",
            expected_codes=("SFA002",),
            expected_lines=(1,),
        ),
    ],
    ids=lambda case: case.description,
)
def test_given_functions_when_checking_annotations_then_flags_only_missing_returns(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    test_case: AnnotationRuleTestCase,
) -> None:
    result: EvaluationResult = evaluate_annotation_test_case(
        test_case=test_case, tmp_path=tmp_path, monkeypatch=monkeypatch
    )

    assert tuple(fault.code for fault in result.faults) == test_case.expected_codes
    assert tuple(fault.line for fault in result.faults) == test_case.expected_lines


@pytest.mark.parametrize(
    "test_case",
    [
        AnnotationRuleTestCase(
            description="module variable assignment is flagged",
            rule_code="SFA101",
            source="value = 1\n",
            expected_codes=("SFA101",),
            expected_lines=(1,),
        ),
        AnnotationRuleTestCase(
            description="module dunder assignments are exempt",
            rule_code="SFA101",
            source="__all__ = ['value']\n__version__ = '1.0'\n",
            expected_codes=(),
            expected_lines=(),
        ),
        AnnotationRuleTestCase(
            description="annotated module variable is allowed",
            rule_code="SFA101",
            source="value: int = 1\n",
            expected_codes=(),
            expected_lines=(),
        ),
    ],
    ids=lambda case: case.description,
)
def test_given_module_assignments_when_checking_annotations_then_flags_only_unannotated_names(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    test_case: AnnotationRuleTestCase,
) -> None:
    result: EvaluationResult = evaluate_annotation_test_case(
        test_case=test_case, tmp_path=tmp_path, monkeypatch=monkeypatch
    )

    assert tuple(fault.code for fault in result.faults) == test_case.expected_codes
    assert tuple(fault.line for fault in result.faults) == test_case.expected_lines


@pytest.mark.parametrize(
    "test_case",
    [
        AnnotationRuleTestCase(
            description="class attribute assignment is flagged",
            rule_code="SFA102",
            source="class Config:\n    value = 1\n",
            expected_codes=("SFA102",),
            expected_lines=(2,),
        ),
        AnnotationRuleTestCase(
            description="class dunder test metadata assignments are exempt",
            rule_code="SFA102",
            source="class Config:\n    __slots__ = ('value',)\n    __test__ = False\n",
            expected_codes=(),
            expected_lines=(),
        ),
        AnnotationRuleTestCase(
            description="enum member assignments are exempt",
            rule_code="SFA102",
            source="from enum import Enum\n\nclass Color(Enum):\n    RED = 'red'\n",
            expected_codes=(),
            expected_lines=(),
        ),
    ],
    ids=lambda case: case.description,
)
def test_given_class_assignments_when_checking_annotations_then_flags_only_unannotated_attrs(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    test_case: AnnotationRuleTestCase,
) -> None:
    result: EvaluationResult = evaluate_annotation_test_case(
        test_case=test_case, tmp_path=tmp_path, monkeypatch=monkeypatch
    )

    assert tuple(fault.code for fault in result.faults) == test_case.expected_codes
    assert tuple(fault.line for fault in result.faults) == test_case.expected_lines


@pytest.mark.parametrize(
    "test_case",
    [
        AnnotationRuleTestCase(
            description="local variable first assignment is flagged",
            rule_code="SFA103",
            source="def run() -> None:\n    value = 1\n",
            expected_codes=("SFA103",),
            expected_lines=(2,),
        ),
        AnnotationRuleTestCase(
            description="underscore local assignment is exempt",
            rule_code="SFA103",
            source="def run() -> None:\n    _ = 1\n",
            expected_codes=(),
            expected_lines=(),
        ),
        AnnotationRuleTestCase(
            description="annotated local first binding then reassignment is allowed",
            rule_code="SFA103",
            source="def run() -> None:\n    value: int = 1\n    value = 2\n",
            expected_codes=(),
            expected_lines=(),
        ),
        AnnotationRuleTestCase(
            description="nested class attribute does not bind its enclosing function local",
            rule_code="SFA103",
            source=("def run() -> None:\n    class Config:\n        value = 1\n    value = 2\n"),
            expected_codes=("SFA103",),
            expected_lines=(4,),
        ),
        AnnotationRuleTestCase(
            description="locals nested in statement containers are flagged",
            rule_code="SFA103",
            source=(
                "def run(value: int) -> None:\n"
                "    if value:\n"
                "        selected = value\n"
                "    try:\n"
                "        consume(value)\n"
                "    except ValueError:\n"
                "        recovered = value\n"
                "    match value:\n"
                "        case 1:\n"
                "            matched = value\n"
            ),
            expected_codes=("SFA103", "SFA103", "SFA103"),
            expected_lines=(3, 7, 10),
        ),
    ],
    ids=lambda case: case.description,
)
def test_given_local_assignments_when_checking_annotations_then_flags_only_first_bindings(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    test_case: AnnotationRuleTestCase,
) -> None:
    result: EvaluationResult = evaluate_annotation_test_case(
        test_case=test_case, tmp_path=tmp_path, monkeypatch=monkeypatch
    )

    assert tuple(fault.code for fault in result.faults) == test_case.expected_codes
    assert tuple(fault.line for fault in result.faults) == test_case.expected_lines
