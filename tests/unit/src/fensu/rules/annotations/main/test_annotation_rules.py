"""Tests for annotation rules."""

from __future__ import annotations

from pathlib import Path

import pytest

import fensu.rules.annotations.main._annotation_rules as annotation_rules_module
from fensu.evaluation.models import EvaluationResult
from tests.unit.src.fensu.rules.annotations.main._test_types import AnnotationRuleTestCase
from tests.unit.src.fensu.rules.annotations.main.helpers import evaluate_annotation_test_case


@pytest.mark.parametrize(
    "test_case",
    [
        AnnotationRuleTestCase(
            description="unannotated parameter is flagged",
            rule_code="FFA001",
            source="def run(value) -> None:\n    return None\n",
            expected_codes=("FFA001",),
            expected_lines=(1,),
        ),
        AnnotationRuleTestCase(
            description="method self parameter is exempt",
            rule_code="FFA001",
            source="class Service:\n    def run(self, value: int) -> None:\n        return None\n",
            expected_codes=(),
            expected_lines=(),
        ),
        AnnotationRuleTestCase(
            description="unannotated vararg and kwarg are flagged",
            rule_code="FFA001",
            source="def run(*items, **kwargs) -> None:\n    return None\n",
            expected_codes=("FFA001", "FFA001"),
            expected_lines=(1, 1),
        ),
        AnnotationRuleTestCase(
            description="async unannotated parameter is flagged",
            rule_code="FFA001",
            source="async def run(value) -> None:\n    return None\n",
            expected_codes=("FFA001",),
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
            description="Python oracle golden preserves complete parameter diagnostics",
            rule_code="FFA001",
            source=(
                "def run(value, *items, **kwargs) -> None:\n"
                "    return None\n\n"
                "class Service:\n"
                "    def method(self, typed: int) -> None:\n"
                "        return None\n\n"
                "async def fetch(payload) -> None:\n"
                "    return None\n"
            ),
            expected_codes=("FFA001", "FFA001", "FFA001", "FFA001"),
            expected_lines=(1, 1, 1, 8),
            expected_faults=(
                (
                    "FFA001",
                    1,
                    8,
                    "function parameter 'value' must define a type annotation",
                    "Annotate every parameter with the value type accepted by the function.",
                ),
                (
                    "FFA001",
                    1,
                    16,
                    "function parameter 'items' must define a type annotation",
                    "Annotate every parameter with the value type accepted by the function.",
                ),
                (
                    "FFA001",
                    1,
                    25,
                    "function parameter 'kwargs' must define a type annotation",
                    "Annotate every parameter with the value type accepted by the function.",
                ),
                (
                    "FFA001",
                    8,
                    16,
                    "function parameter 'payload' must define a type annotation",
                    "Annotate every parameter with the value type accepted by the function.",
                ),
            ),
        )
    ],
    ids=lambda case: case.description,
)
def test_given_python_oracle_golden_when_checking_native_rule_then_output_is_identical(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    test_case: AnnotationRuleTestCase,
) -> None:
    result: EvaluationResult = evaluate_annotation_test_case(
        test_case=test_case, tmp_path=tmp_path, monkeypatch=monkeypatch
    )

    actual_faults: tuple[tuple[str, int | None, int | None, str, str | None], ...] = tuple(
        (fault.code, fault.line, fault.column, fault.message, fault.remediation)
        for fault in result.faults
    )
    assert actual_faults == test_case.expected_faults


@pytest.mark.parametrize(
    "test_case",
    [
        AnnotationRuleTestCase(
            description="registered native rule has no Python core callback",
            rule_code="FFA001",
            source="def run(value) -> None:\n    return None\n",
            expected_codes=("FFA001",),
            expected_lines=(1,),
        )
    ],
    ids=lambda case: case.description,
)
def test_given_registered_native_rule_when_evaluating_then_has_no_python_callback(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    test_case: AnnotationRuleTestCase,
) -> None:
    result: EvaluationResult = evaluate_annotation_test_case(
        test_case=test_case, tmp_path=tmp_path, monkeypatch=monkeypatch
    )

    assert tuple(fault.code for fault in result.faults) == test_case.expected_codes
    assert all(rule.check is None for rule in annotation_rules_module.annotation_rules())


@pytest.mark.parametrize(
    "test_case",
    [
        AnnotationRuleTestCase(
            description="missing return annotation is flagged",
            rule_code="FFA002",
            source="def run(value: int):\n    return None\n",
            expected_codes=("FFA002",),
            expected_lines=(1,),
        ),
        AnnotationRuleTestCase(
            description="return annotation is allowed",
            rule_code="FFA002",
            source="def run(value: int) -> None:\n    return None\n",
            expected_codes=(),
            expected_lines=(),
        ),
        AnnotationRuleTestCase(
            description="async missing return annotation is flagged",
            rule_code="FFA002",
            source="async def run(value: int):\n    return None\n",
            expected_codes=("FFA002",),
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
            rule_code="FFA101",
            source="value = 1\n",
            expected_codes=("FFA101",),
            expected_lines=(1,),
        ),
        AnnotationRuleTestCase(
            description="module dunder assignments are exempt",
            rule_code="FFA101",
            source="__all__ = ['value']\n__version__ = '1.0'\n",
            expected_codes=(),
            expected_lines=(),
        ),
        AnnotationRuleTestCase(
            description="annotated module variable is allowed",
            rule_code="FFA101",
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
            rule_code="FFA102",
            source="class Config:\n    value = 1\n",
            expected_codes=("FFA102",),
            expected_lines=(2,),
        ),
        AnnotationRuleTestCase(
            description="class dunder test metadata assignments are exempt",
            rule_code="FFA102",
            source="class Config:\n    __slots__ = ('value',)\n    __test__ = False\n",
            expected_codes=(),
            expected_lines=(),
        ),
        AnnotationRuleTestCase(
            description="enum member assignments are exempt",
            rule_code="FFA102",
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
            description="local variable assigned a call is flagged",
            rule_code="FFA103",
            source="def run() -> None:\n    value = build_value()\n",
            expected_codes=("FFA103",),
            expected_lines=(2,),
        ),
        AnnotationRuleTestCase(
            description="scalar literal local assignments are exempt",
            rule_code="FFA103",
            source=(
                "def run(number: int) -> None:\n"
                "    integer = 1\n"
                "    floating = 1.5\n"
                "    negative = -1.5\n"
                "    positive = +3\n"
                "    imaginary = 2j\n"
                "    text = 'value'\n"
                "    binary = b'value'\n"
                "    enabled = True\n"
                "    formatted = f'value-{number}'\n"
                "    nested_unary = --1\n"
            ),
            expected_codes=(),
            expected_lines=(),
        ),
        AnnotationRuleTestCase(
            description="none and ellipsis local assignments require annotations",
            rule_code="FFA103",
            source="def run() -> None:\n    missing = None\n    omitted = ...\n",
            expected_codes=("FFA103", "FFA103"),
            expected_lines=(2, 3),
        ),
        AnnotationRuleTestCase(
            description="container local assignments require annotations",
            rule_code="FFA103",
            source=(
                "def run() -> None:\n"
                "    empty_list = []\n"
                "    empty_dict = {}\n"
                "    empty_set = set()\n"
                "    empty_tuple = ()\n"
                "    populated = [1, 2]\n"
            ),
            expected_codes=("FFA103", "FFA103", "FFA103", "FFA103", "FFA103"),
            expected_lines=(2, 3, 4, 5, 6),
        ),
        AnnotationRuleTestCase(
            description="computed local assignments require annotations",
            rule_code="FFA103",
            source=(
                "def run(value: int, obj: object, values: dict[str, int]) -> None:\n"
                "    attribute = obj.value\n"
                "    item = values['key']\n"
                "    comprehension = [item for item in values]\n"
                "    conditional = 1 if value else 2\n"
                "    concatenated = 'a' + 'b'\n"
            ),
            expected_codes=("FFA103", "FFA103", "FFA103", "FFA103", "FFA103"),
            expected_lines=(2, 3, 4, 5, 6),
        ),
        AnnotationRuleTestCase(
            description="multiple assignment of scalar literal requires annotations",
            rule_code="FFA103",
            source="def run() -> None:\n    first = second = 1\n",
            expected_codes=("FFA103", "FFA103"),
            expected_lines=(2, 2),
        ),
        AnnotationRuleTestCase(
            description="augmented first assignment requires annotation",
            rule_code="FFA103",
            source="def run() -> None:\n    value += 1\n",
            expected_codes=("FFA103",),
            expected_lines=(2,),
        ),
        AnnotationRuleTestCase(
            description="underscore local assignment is exempt",
            rule_code="FFA103",
            source="def run() -> None:\n    _ = 1\n",
            expected_codes=(),
            expected_lines=(),
        ),
        AnnotationRuleTestCase(
            description="annotated local first binding then reassignment is allowed",
            rule_code="FFA103",
            source="def run() -> None:\n    value: int = 1\n    value = 2\n",
            expected_codes=(),
            expected_lines=(),
        ),
        AnnotationRuleTestCase(
            description="nested class attribute does not bind its enclosing function local",
            rule_code="FFA103",
            source=(
                "def run() -> None:\n"
                "    class Config:\n"
                "        value = 1\n"
                "    value = build_value()\n"
            ),
            expected_codes=("FFA103",),
            expected_lines=(4,),
        ),
        AnnotationRuleTestCase(
            description="locals nested in statement containers are flagged",
            rule_code="FFA103",
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
            expected_codes=("FFA103", "FFA103", "FFA103"),
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
