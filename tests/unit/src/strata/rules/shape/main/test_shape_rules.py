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
            description="discarded local meaningful result is flagged",
            rule_code="SFS101",
            source=(
                "def compile_project() -> int:\n"
                "    return 1\n\n\n"
                "def run() -> None:\n"
                "    compile_project()\n"
            ),
            expected_codes=("SFS101",),
            expected_lines=(6,),
        ),
        ShapeRuleTestCase(
            description="none and no-return project calls are allowed",
            rule_code="SFS101",
            source=(
                "from typing import NoReturn\n\n\n"
                "def validate_project() -> None:\n"
                "    return None\n\n\n"
                "def stop_project() -> NoReturn:\n"
                "    raise RuntimeError\n\n\n"
                "def run() -> None:\n"
                "    validate_project()\n"
                "    stop_project()\n"
            ),
            expected_codes=(),
            expected_lines=(),
        ),
        ShapeRuleTestCase(
            description="missing and unresolved return contracts are outside the rule",
            rule_code="SFS101",
            source=(
                "def local_unknown():\n"
                "    return 1\n\n\n"
                "def run(*, parser: object) -> None:\n"
                "    local_unknown()\n"
                "    external_function()\n"
                "    parser.add_argument('path')\n"
            ),
            expected_codes=(),
            expected_lines=(),
        ),
        ShapeRuleTestCase(
            description="discarded directly imported meaningful result is flagged",
            rule_code="SFS101",
            source=(
                "from pkg.domain.core.helpers.phases import compile_project\n\n\n"
                "def run() -> None:\n"
                "    compile_project()\n"
            ),
            project_files=(
                (
                    "domain/core/helpers/phases.py",
                    "def compile_project() -> int:\n    return 1\n",
                ),
            ),
            expected_codes=("SFS101",),
            expected_lines=(5,),
        ),
        ShapeRuleTestCase(
            description="discarded imported result resolves under a python container",
            rule_code="SFS101",
            source=(
                "from mypkg.domain.core.helpers.phases import compile_project\n\n\n"
                "def run() -> None:\n"
                "    compile_project()\n"
            ),
            project_files=(
                (
                    "domain/core/helpers/phases.py",
                    "def compile_project() -> int:\n    return 1\n",
                ),
            ),
            expected_codes=("SFS101",),
            expected_lines=(5,),
            root="python/mypkg",
        ),
        ShapeRuleTestCase(
            description="discarded module-qualified meaningful result is flagged",
            rule_code="SFS101",
            source=(
                "import pkg.domain.core.helpers.phases as phases\n\n\n"
                "def run() -> None:\n"
                "    phases.compile_project()\n"
            ),
            project_files=(
                (
                    "domain/core/helpers/phases.py",
                    "def compile_project() -> int:\n    return 1\n",
                ),
            ),
            expected_codes=("SFS101",),
            expected_lines=(5,),
        ),
        ShapeRuleTestCase(
            description="assignment return and explicit discard consume meaningful results",
            rule_code="SFS101",
            source=(
                "def compile_project() -> int:\n"
                "    return 1\n\n\n"
                "def run() -> int:\n"
                "    project: int = compile_project()\n"
                "    _ = compile_project()\n"
                "    return compile_project()\n"
            ),
            expected_codes=(),
            expected_lines=(),
        ),
        ShapeRuleTestCase(
            description="nested function calls are outside the orchestrator body",
            rule_code="SFS101",
            source=(
                "def compile_project() -> int:\n"
                "    return 1\n\n\n"
                "def run() -> None:\n"
                "    def nested() -> None:\n"
                "        compile_project()\n\n"
                "    nested()\n"
            ),
            expected_codes=(),
            expected_lines=(),
        ),
        ShapeRuleTestCase(
            description="discarded awaited meaningful result is flagged",
            rule_code="SFS101",
            source=(
                "async def fetch_project() -> int:\n"
                "    return 1\n\n\n"
                "async def run() -> None:\n"
                "    await fetch_project()\n"
            ),
            expected_codes=("SFS101",),
            expected_lines=(6,),
        ),
        ShapeRuleTestCase(
            description="validator name does not hide a meaningful return",
            rule_code="SFS101",
            source=(
                "def validate_project() -> bool:\n"
                "    return True\n\n\n"
                "def run() -> None:\n"
                "    validate_project()\n"
            ),
            expected_codes=("SFS101",),
            expected_lines=(6,),
        ),
        ShapeRuleTestCase(
            description="locally shadowed function names are unresolved",
            rule_code="SFS101",
            source=(
                "def compile_project() -> int:\n"
                "    return 1\n\n\n"
                "def run(*, compile_project: object) -> None:\n"
                "    compile_project()\n"
            ),
            expected_codes=(),
            expected_lines=(),
        ),
    ],
    ids=lambda case: case.description,
)
def test_given_main_calls_when_checking_results_then_flags_discarded_project_values(
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
            description="module-global collection mutation is flagged",
            rule_code="SFS130",
            source="CACHE: list[int] = []\n\ndef run() -> None:\n    CACHE.append(1)\n",
            expected_codes=("SFS130",),
            expected_lines=(4,),
        ),
        ShapeRuleTestCase(
            description="module-global subscript mutation is flagged",
            rule_code="SFS130",
            source="CACHE: dict[str, int] = {}\n\ndef run() -> None:\n    CACHE['x'] = 1\n",
            expected_codes=("SFS130",),
            expected_lines=(4,),
        ),
        ShapeRuleTestCase(
            description="module-global attribute mutation is flagged",
            rule_code="SFS130",
            source="STATE: object = object()\n\ndef run() -> None:\n    STATE.value = 1\n",
            expected_codes=("SFS130",),
            expected_lines=(4,),
        ),
        ShapeRuleTestCase(
            description="explicit global rebinding is flagged",
            rule_code="SFS130",
            source="COUNT: int = 0\n\ndef run() -> None:\n    global COUNT\n    COUNT = 1\n",
            expected_codes=("SFS130",),
            expected_lines=(5,),
        ),
        ShapeRuleTestCase(
            description="new explicit global binding is flagged",
            rule_code="SFS130",
            source="def run() -> None:\n    global CREATED\n    CREATED = 1\n",
            expected_codes=("SFS130",),
            expected_lines=(3,),
        ),
        ShapeRuleTestCase(
            description="global declarations do not make another function local assignment outer",
            rule_code="SFS130",
            source=(
                "COUNT: int = 0\n\n"
                "def local() -> None:\n"
                "    value = 1\n\n"
                "def update() -> None:\n"
                "    global COUNT\n"
                "    COUNT = 1\n"
            ),
            expected_codes=("SFS130",),
            expected_lines=(8,),
        ),
        ShapeRuleTestCase(
            description="closure collection mutation is flagged",
            rule_code="SFS130",
            source=(
                "def outer() -> None:\n"
                "    values: list[int] = []\n"
                "    def inner() -> None:\n"
                "        values.append(1)\n"
            ),
            expected_codes=("SFS130",),
            expected_lines=(4,),
        ),
        ShapeRuleTestCase(
            description="explicit nonlocal rebinding is flagged",
            rule_code="SFS130",
            source=(
                "def outer() -> None:\n"
                "    count: int = 0\n"
                "    def inner() -> None:\n"
                "        nonlocal count\n"
                "        count = 1\n"
            ),
            expected_codes=("SFS130",),
            expected_lines=(5,),
        ),
        ShapeRuleTestCase(
            description="local collection mutation is allowed",
            rule_code="SFS130",
            source="def run() -> None:\n    values: list[int] = []\n    values.append(1)\n",
            expected_codes=(),
            expected_lines=(),
        ),
        ShapeRuleTestCase(
            description="local binding shadows a module binding with the same name",
            rule_code="SFS130",
            source=(
                "CACHE: list[int] = []\n\n"
                "def run() -> None:\n"
                "    CACHE: list[int] = []\n"
                "    CACHE.append(1)\n"
            ),
            expected_codes=(),
            expected_lines=(),
        ),
        ShapeRuleTestCase(
            description="parameter and self mutation are allowed",
            rule_code="SFS130",
            source=(
                "class Service:\n"
                "    def update(self, values: list[int]) -> None:\n"
                "        self.ready = True\n"
                "        values.append(1)\n"
            ),
            expected_codes=(),
            expected_lines=(),
        ),
        ShapeRuleTestCase(
            description="reading outer state is allowed",
            rule_code="SFS130",
            source="VALUE: int = 1\n\ndef read() -> int:\n    return VALUE\n",
            expected_codes=(),
            expected_lines=(),
        ),
        ShapeRuleTestCase(
            description="alias-through-local mutation remains outside initial detection",
            rule_code="SFS130",
            source=(
                "CACHE: list[int] = []\n\n"
                "def run() -> None:\n"
                "    values: list[int] = CACHE\n"
                "    values.append(1)\n"
            ),
            expected_codes=(),
            expected_lines=(),
        ),
        ShapeRuleTestCase(
            description="comprehension target shadows module binding",
            rule_code="SFS130",
            source=(
                "VALUES: list[list[int]] = []\n\n"
                "def run(*, rows: list[list[int]]) -> list[None]:\n"
                "    return [VALUES.append(1) for VALUES in rows]\n"
            ),
            expected_codes=(),
            expected_lines=(),
        ),
        ShapeRuleTestCase(
            description="outer mutation inside comprehension is flagged",
            rule_code="SFS130",
            source=(
                "CACHE: list[int] = []\n\n"
                "def run(*, rows: list[int]) -> list[None]:\n"
                "    return [CACHE.append(item) for item in rows]\n"
            ),
            expected_codes=("SFS130",),
            expected_lines=(4,),
        ),
        ShapeRuleTestCase(
            description="module-bound class state mutation is flagged",
            rule_code="SFS130",
            source=(
                "class Registry:\n"
                "    values: list[int] = []\n\n"
                "def run() -> None:\n"
                "    Registry.values.append(1)\n"
            ),
            expected_codes=("SFS130",),
            expected_lines=(5,),
        ),
        ShapeRuleTestCase(
            description="imported infrastructure state is outside project-owned globals",
            rule_code="SFS130",
            source=(
                "import external_state\n\ndef run() -> None:\n    external_state.CACHE.append(1)\n"
            ),
            expected_codes=(),
            expected_lines=(),
        ),
    ],
    ids=lambda case: case.description,
)
def test_given_function_state_when_checking_mutation_then_flags_only_outer_bindings(
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
            description="list comprehension with two generators is flagged",
            rule_code="SFS131",
            source=(
                "def run() -> list[tuple[int, int]]:\n"
                "    return [(left, right) for left in (1, 2) for right in (3, 4)]\n"
            ),
            expected_codes=("SFS131",),
            expected_lines=(2,),
        ),
        ShapeRuleTestCase(
            description="comprehension containing another comprehension is flagged",
            rule_code="SFS131",
            source=(
                "def run(rows: list[list[int]]) -> list[list[int]]:\n"
                "    return [[value * 2 for value in row] for row in rows]\n"
            ),
            expected_codes=("SFS131",),
            expected_lines=(2,),
        ),
        ShapeRuleTestCase(
            description="tuple generator with two generators is flagged",
            rule_code="SFS131",
            source=(
                "def run() -> tuple[tuple[int, int], ...]:\n"
                "    return tuple((left, right) for left in (1, 2) for right in (3, 4))\n"
            ),
            expected_codes=("SFS131",),
            expected_lines=(2,),
        ),
        ShapeRuleTestCase(
            description="single filtered comprehension is allowed in product code",
            rule_code="SFS131",
            source=(
                "def run(values: list[int]) -> list[int]:\n"
                "    return [value for value in values if value > 0]\n"
            ),
            expected_codes=(),
            expected_lines=(),
        ),
        ShapeRuleTestCase(
            description="sequential single-generator comprehensions are allowed",
            rule_code="SFS131",
            source=(
                "def run(values: list[int]) -> list[int]:\n"
                "    doubled: list[int] = [value * 2 for value in values]\n"
                "    return [value + 1 for value in doubled]\n"
            ),
            expected_codes=(),
            expected_lines=(),
        ),
    ],
    ids=lambda case: case.description,
)
def test_given_comprehensions_when_checking_shape_then_flags_only_complex_forms(
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
