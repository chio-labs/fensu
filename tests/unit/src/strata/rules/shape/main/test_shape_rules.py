"""Tests for shape rules."""

from __future__ import annotations

from pathlib import Path

import pytest

from strata.evaluation.core.models import EvaluationResult
from strata.rules.authoring.types import Threshold
from tests.unit.src.strata.rules.shape.main._test_types import ShapeRuleTestCase
from tests.unit.src.strata.rules.shape.main.helpers import (
    calls_source,
    evaluate_shape_test_case,
    locals_source,
    statements_source,
)


@pytest.mark.parametrize(
    "test_case",
    [
        ShapeRuleTestCase(
            description="main function over statement limit is flagged",
            rule_code="SFS001",
            source=statements_source(41),
            expected_codes=("SFS001",),
            expected_lines=(1,),
        ),
        ShapeRuleTestCase(
            description="main function at statement limit is allowed",
            rule_code="SFS001",
            source=statements_source(40),
            expected_codes=(),
            expected_lines=(),
        ),
        ShapeRuleTestCase(
            description="private main function over statement limit is flagged",
            rule_code="SFS001",
            source=statements_source(41).replace("def run", "def _run"),
            expected_codes=("SFS001",),
            expected_lines=(1,),
        ),
        ShapeRuleTestCase(
            description="main role threshold override is respected",
            rule_code="SFS001",
            source=statements_source(31),
            expected_codes=("SFS001",),
            expected_lines=(1,),
            role_thresholds={"main": {Threshold.MAX_STATEMENTS: 30}},
        ),
    ],
    ids=lambda case: case.description,
)
def test_given_main_functions_when_checking_statements_then_flags_only_over_limit(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    test_case: ShapeRuleTestCase,
) -> None:
    result: EvaluationResult = evaluate_shape_test_case(
        test_case=test_case, tmp_path=tmp_path, monkeypatch=monkeypatch
    )

    assert tuple(fault.code for fault in result.faults) == test_case.expected_codes
    assert tuple(fault.line for fault in result.faults) == test_case.expected_lines


@pytest.mark.parametrize(
    "test_case",
    [
        ShapeRuleTestCase(
            description="main function over distinct call limit is flagged",
            rule_code="SFS002",
            source=calls_source(21),
            expected_codes=("SFS002",),
            expected_lines=(64,),
        ),
        ShapeRuleTestCase(
            description="main function at distinct call limit is allowed",
            rule_code="SFS002",
            source=calls_source(20),
            expected_codes=(),
            expected_lines=(),
        ),
    ],
    ids=lambda case: case.description,
)
def test_given_main_functions_when_checking_calls_then_flags_only_over_limit(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    test_case: ShapeRuleTestCase,
) -> None:
    result: EvaluationResult = evaluate_shape_test_case(
        test_case=test_case, tmp_path=tmp_path, monkeypatch=monkeypatch
    )

    assert tuple(fault.code for fault in result.faults) == test_case.expected_codes
    assert tuple(fault.line for fault in result.faults) == test_case.expected_lines


@pytest.mark.parametrize(
    "test_case",
    [
        ShapeRuleTestCase(
            description="main function over local limit is flagged",
            rule_code="SFS003",
            source=locals_source(21),
            expected_codes=("SFS003",),
            expected_lines=(1,),
        ),
        ShapeRuleTestCase(
            description="main function at local limit is allowed",
            rule_code="SFS003",
            source=locals_source(20),
            expected_codes=(),
            expected_lines=(),
        ),
    ],
    ids=lambda case: case.description,
)
def test_given_main_functions_when_checking_locals_then_flags_only_over_limit(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    test_case: ShapeRuleTestCase,
) -> None:
    result: EvaluationResult = evaluate_shape_test_case(
        test_case=test_case, tmp_path=tmp_path, monkeypatch=monkeypatch
    )

    assert tuple(fault.code for fault in result.faults) == test_case.expected_codes
    assert tuple(fault.line for fault in result.faults) == test_case.expected_lines


@pytest.mark.parametrize(
    "test_case",
    [
        ShapeRuleTestCase(
            description="function with eleven arguments is flagged",
            rule_code="SFS010",
            source="def run(a: int, b: int, c: int, d: int, e: int, f: int, g: int, h: int, i: int, j: int, k: int) -> None:\n    return None\n",
            expected_codes=("SFS010",),
            expected_lines=(1,),
            relative_path="domain/core/helpers/tools.py",
        ),
        ShapeRuleTestCase(
            description="method self is exempt from argument count",
            rule_code="SFS010",
            source="class Service:\n    def run(self, a: int, b: int, c: int, d: int, e: int, f: int, g: int, h: int, i: int, j: int) -> None:\n        return None\n",
            expected_codes=(),
            expected_lines=(),
            relative_path="domain/core/helpers/tools.py",
        ),
        ShapeRuleTestCase(
            description="helper role argument threshold override is respected",
            rule_code="SFS010",
            source="def run(first: int, second: int) -> None:\n    return None\n",
            expected_codes=("SFS010",),
            expected_lines=(1,),
            role_thresholds={"helpers": {Threshold.MAX_ARGUMENTS: 1}},
            relative_path="domain/core/helpers/tools.py",
        ),
    ],
    ids=lambda case: case.description,
)
def test_given_functions_when_checking_arguments_then_flags_only_over_limit(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    test_case: ShapeRuleTestCase,
) -> None:
    result: EvaluationResult = evaluate_shape_test_case(
        test_case=test_case, tmp_path=tmp_path, monkeypatch=monkeypatch
    )

    assert tuple(fault.code for fault in result.faults) == test_case.expected_codes
    assert tuple(fault.line for fault in result.faults) == test_case.expected_lines


@pytest.mark.parametrize(
    "test_case",
    [
        ShapeRuleTestCase(
            description="helper over global statement floor is flagged",
            rule_code="SFS011",
            source=statements_source(71),
            expected_codes=("SFS011",),
            expected_lines=(1,),
            relative_path="domain/core/helpers/tools.py",
        ),
        ShapeRuleTestCase(
            description="helper at global statement floor is allowed",
            rule_code="SFS011",
            source=statements_source(70),
            expected_codes=(),
            expected_lines=(),
            relative_path="domain/core/helpers/tools.py",
        ),
        ShapeRuleTestCase(
            description="main function above tight limit but below global floor is allowed",
            rule_code="SFS011",
            source=statements_source(45),
            expected_codes=(),
            expected_lines=(),
        ),
    ],
    ids=lambda case: case.description,
)
def test_given_functions_when_checking_global_statements_then_flags_only_over_limit(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    test_case: ShapeRuleTestCase,
) -> None:
    result: EvaluationResult = evaluate_shape_test_case(
        test_case=test_case, tmp_path=tmp_path, monkeypatch=monkeypatch
    )

    assert tuple(fault.code for fault in result.faults) == test_case.expected_codes
    assert tuple(fault.line for fault in result.faults) == test_case.expected_lines


@pytest.mark.parametrize(
    "test_case",
    [
        ShapeRuleTestCase(
            description="discarded plain call is flagged",
            rule_code="SFS101",
            source="def run() -> None:\n    build_value()\n\ndef build_value() -> int:\n    return 1\n",
            expected_codes=("SFS101",),
            expected_lines=(2,),
        ),
        ShapeRuleTestCase(
            description="validator and assignment calls are allowed",
            rule_code="SFS101",
            source="def run() -> None:\n    validate_value()\n    value: int = build_value()\n    _ = build_value()\n\ndef validate_value() -> None:\n    return None\n\ndef build_value() -> int:\n    return 1\n",
            expected_codes=(),
            expected_lines=(),
        ),
    ],
    ids=lambda case: case.description,
)
def test_given_main_calls_when_checking_discarded_results_then_flags_plain_discards(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    test_case: ShapeRuleTestCase,
) -> None:
    result: EvaluationResult = evaluate_shape_test_case(
        test_case=test_case, tmp_path=tmp_path, monkeypatch=monkeypatch
    )

    assert tuple(fault.code for fault in result.faults) == test_case.expected_codes
    assert tuple(fault.line for fault in result.faults) == test_case.expected_lines


@pytest.mark.parametrize(
    "test_case",
    [
        ShapeRuleTestCase(
            description="helper parameter mutation is flagged when enabled",
            rule_code="SFS102",
            source="def update(values: list[int]) -> None:\n    values.append(1)\n",
            expected_codes=("SFS102",),
            expected_lines=(2,),
            relative_path="domain/core/helpers/tools.py",
        ),
        ShapeRuleTestCase(
            description="self mutation is exempt in helper",
            rule_code="SFS102",
            source="class Builder:\n    def update(self) -> None:\n        self.values.append(1)\n",
            expected_codes=(),
            expected_lines=(),
            relative_path="domain/core/helpers/tools.py",
        ),
    ],
    ids=lambda case: case.description,
)
def test_given_helper_parameter_mutation_when_rule_enabled_then_flags_non_self_mutation(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    test_case: ShapeRuleTestCase,
) -> None:
    result: EvaluationResult = evaluate_shape_test_case(
        test_case=test_case, tmp_path=tmp_path, monkeypatch=monkeypatch
    )

    assert tuple(fault.code for fault in result.faults) == test_case.expected_codes
    assert tuple(fault.line for fault in result.faults) == test_case.expected_lines


@pytest.mark.parametrize(
    "test_case",
    [
        ShapeRuleTestCase(
            description="parameter mutation without return is flagged",
            rule_code="SFS110",
            source="def update(values: list[int]) -> None:\n    values.append(1)\n",
            expected_codes=("SFS110",),
            expected_lines=(2,),
            relative_path="domain/core/helpers/tools.py",
        ),
        ShapeRuleTestCase(
            description="parameter mutation with return is allowed",
            rule_code="SFS110",
            source="def update(values: list[int]) -> list[int]:\n    values.append(1)\n    return values\n",
            expected_codes=(),
            expected_lines=(),
            relative_path="domain/core/helpers/tools.py",
        ),
        ShapeRuleTestCase(
            description="two parameter mutation returning one is flagged once",
            rule_code="SFS110",
            source="def update(left: list[int], right: list[int]) -> list[int]:\n    left.append(1)\n    right.append(2)\n    return left\n",
            expected_codes=("SFS110",),
            expected_lines=(3,),
            relative_path="domain/core/helpers/tools.py",
        ),
        ShapeRuleTestCase(
            description="property setter mutation is exempt",
            rule_code="SFS110",
            source="class Service:\n    @value.setter\n    def value(self, item: list[int]) -> None:\n        item.append(1)\n",
            expected_codes=(),
            expected_lines=(),
            relative_path="domain/core/helpers/tools.py",
        ),
        ShapeRuleTestCase(
            description="subscript parameter mutation is flagged",
            rule_code="SFS110",
            source="def update(values: list[int]) -> None:\n    values[0] = 1\n",
            expected_codes=("SFS110",),
            expected_lines=(2,),
            relative_path="domain/core/helpers/tools.py",
        ),
        ShapeRuleTestCase(
            description="attribute parameter mutation is flagged",
            rule_code="SFS110",
            source="def update(config: object) -> None:\n    config.value = 1\n",
            expected_codes=("SFS110",),
            expected_lines=(2,),
            relative_path="domain/core/helpers/tools.py",
        ),
        ShapeRuleTestCase(
            description="dunder parameter mutation is exempt",
            rule_code="SFS110",
            source="class Value:\n    def __setitem__(self, key: str, value: int) -> None:\n        value.real = 1\n",
            expected_codes=(),
            expected_lines=(),
            relative_path="domain/core/helpers/tools.py",
        ),
    ],
    ids=lambda case: case.description,
)
def test_given_parameter_mutation_when_checking_returns_then_requires_all_mutated_params(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    test_case: ShapeRuleTestCase,
) -> None:
    result: EvaluationResult = evaluate_shape_test_case(
        test_case=test_case, tmp_path=tmp_path, monkeypatch=monkeypatch
    )

    assert tuple(fault.code for fault in result.faults) == test_case.expected_codes
    assert tuple(fault.line for fault in result.faults) == test_case.expected_lines


@pytest.mark.parametrize(
    "test_case",
    [
        ShapeRuleTestCase(
            description="positional parameter at default threshold is flagged",
            rule_code="SFS120",
            source="def run(value: int) -> None:\n    return None\n",
            expected_codes=("SFS120",),
            expected_lines=(1,),
            relative_path="domain/core/helpers/tools.py",
        ),
        ShapeRuleTestCase(
            description="keyword-only parameter is allowed",
            rule_code="SFS120",
            source="def run(*, value: int) -> None:\n    return None\n",
            expected_codes=(),
            expected_lines=(),
            relative_path="domain/core/helpers/tools.py",
        ),
        ShapeRuleTestCase(
            description="dunder positional parameter is exempt",
            rule_code="SFS120",
            source="class Value:\n    def __eq__(self, other: object) -> bool:\n        return False\n",
            expected_codes=(),
            expected_lines=(),
            relative_path="domain/core/helpers/tools.py",
        ),
        ShapeRuleTestCase(
            description="threshold allows one positional parameter",
            rule_code="SFS120",
            source="def run(value: int) -> None:\n    return None\n",
            expected_codes=(),
            expected_lines=(),
            thresholds={Threshold.MAX_POSITIONAL_ARGS: 1},
            relative_path="domain/core/helpers/tools.py",
        ),
        ShapeRuleTestCase(
            description="helper role positional threshold override is respected",
            rule_code="SFS120",
            source="def run(value: int) -> None:\n    return None\n",
            expected_codes=(),
            expected_lines=(),
            role_thresholds={"helpers": {Threshold.MAX_POSITIONAL_ARGS: 1}},
            relative_path="domain/core/helpers/tools.py",
        ),
    ],
    ids=lambda case: case.description,
)
def test_given_function_parameters_when_checking_keyword_only_then_flags_excess_positionals(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    test_case: ShapeRuleTestCase,
) -> None:
    result: EvaluationResult = evaluate_shape_test_case(
        test_case=test_case, tmp_path=tmp_path, monkeypatch=monkeypatch
    )

    assert tuple(fault.code for fault in result.faults) == test_case.expected_codes
    assert tuple(fault.line for fault in result.faults) == test_case.expected_lines


@pytest.mark.parametrize(
    "test_case",
    [
        ShapeRuleTestCase(
            description="mutable dataclass model is flagged",
            rule_code="SFS201",
            source="from dataclasses import dataclass\n\n@dataclass\nclass Result:\n    value: int\n",
            expected_codes=("SFS201",),
            expected_lines=(4,),
            relative_path="domain/core/models.py",
        ),
        ShapeRuleTestCase(
            description="frozen dataclass model is allowed",
            rule_code="SFS201",
            source="from dataclasses import dataclass\n\n@dataclass(frozen=True)\nclass Result:\n    value: int\n",
            expected_codes=(),
            expected_lines=(),
            relative_path="domain/core/models.py",
        ),
        ShapeRuleTestCase(
            description="pydantic model is allowed",
            rule_code="SFS201",
            source="from pydantic import BaseModel\n\nclass Result(BaseModel):\n    value: int\n",
            expected_codes=(),
            expected_lines=(),
            relative_path="domain/core/models.py",
        ),
    ],
    ids=lambda case: case.description,
)
def test_given_models_when_checking_mutability_then_flags_only_mutable_dataclasses(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    test_case: ShapeRuleTestCase,
) -> None:
    result: EvaluationResult = evaluate_shape_test_case(
        test_case=test_case, tmp_path=tmp_path, monkeypatch=monkeypatch
    )

    assert tuple(fault.code for fault in result.faults) == test_case.expected_codes
    assert tuple(fault.line for fault in result.faults) == test_case.expected_lines
