"""Integration tests for public custom-rule real-pipeline evaluation."""

from __future__ import annotations

import re
from dataclasses import FrozenInstanceError
from inspect import getattr_static
from pathlib import Path
from typing import Any, cast

import pytest

from strata import RuleCase, RuleFile, RuleResult, evaluate_rule
from strata.analysis.main.select_fact_backend import select_fact_backend
from strata.analysis.types import FactBackend
from strata.instrumentation.constants import OPERATION_COUNTERS, PARSE_OPERATION
from strata.rules.authoring.exceptions import RuleDefinitionError
from strata.rules.testing.exceptions import RuleHarnessError
from tests.integration.src.strata.rules.testing._test_types import (
    FrozenHarnessModelTestCase,
    HarnessEvaluationTestCase,
    HarnessMisuseTestCase,
)
from tests.integration.src.strata.rules.testing.helpers import (
    all_context_zones,
    always_fault,
    context_policy,
    native_assignment_references,
    native_class_declarations,
    native_comparisons,
    native_local_call_edges,
    native_named_calls,
    native_parameter_mutation_occurrences,
    ordinary_ordering,
    undecorated_rule,
)

_RULE_SPEC_ATTRIBUTE: str = "__strata_rule_spec__"

_FACT_FAMILY_CASES: tuple[HarnessEvaluationTestCase, ...] = (
    HarnessEvaluationTestCase(
        description="class declarations support a fact-only custom rule",
        rule=native_class_declarations,
        rule_case=RuleCase(
            description="adapter class",
            source="class ConcreteAdapter(BaseAdapter):\n    pass\n",
            expected_fault_count=1,
        ),
        expected_fault_count=1,
        expected_lines=(1,),
        expected_messages=("adapter class declaration",),
    ),
    HarnessEvaluationTestCase(
        description="assignment references support a fact-only custom rule",
        rule=native_assignment_references,
        rule_case=RuleCase(
            description="adapter member alias",
            source=(
                "class ConcreteAdapter:\n    render_identifier = BaseAdapter.render_identifier\n"
            ),
            expected_fault_count=1,
        ),
        expected_fault_count=1,
        expected_lines=(2,),
        expected_messages=("base adapter assignment reference",),
    ),
    HarnessEvaluationTestCase(
        description="named calls support a fact-only custom rule",
        rule=native_named_calls,
        rule_case=RuleCase(
            description="discarded metadata call",
            source=("def run(rows):\n    for row in rows:\n        metadata.execute('+', row)\n"),
            expected_fault_count=1,
        ),
        expected_fault_count=1,
        expected_lines=(3,),
        expected_messages=("discarded metadata call in loop",),
    ),
    HarnessEvaluationTestCase(
        description="local call edges support a fact-only custom rule",
        rule=native_local_call_edges,
        rule_case=RuleCase(
            description="metadata query edge",
            source=("def run(rows):\n    while rows:\n        query_metadata()\n"),
            expected_fault_count=1,
        ),
        expected_fault_count=1,
        expected_lines=(3,),
        expected_messages=("metadata query call edge in loop",),
    ),
    HarnessEvaluationTestCase(
        description="comparisons support a fact-only custom rule",
        rule=native_comparisons,
        rule_case=RuleCase(
            description="canonical comparison",
            source="if SqlReferenceKind.DBT_REF == kind:\n    pass\n",
            expected_fault_count=1,
        ),
        expected_fault_count=1,
        expected_lines=(1,),
        expected_messages=("canonical reference comparison",),
    ),
    HarnessEvaluationTestCase(
        description="mutation occurrences support a fact-only custom rule",
        rule=native_parameter_mutation_occurrences,
        rule_case=RuleCase(
            description="two parameter mutations",
            source=("def update(values):\n    values.append(1)\n    values.append(2)\n"),
            expected_fault_count=2,
        ),
        expected_fault_count=2,
        expected_lines=(2, 3),
        expected_messages=("parameter mutation occurrence", "parameter mutation occurrence"),
    ),
)

EVALUATION_CASES: tuple[HarnessEvaluationTestCase, ...] = (
    HarnessEvaluationTestCase(
        description="all five context zones and a discovered support module use the real pipeline",
        rule=all_context_zones,
        rule_case=RuleCase(
            description="cross-file public context",
            source="def primary() -> None:\n    pass\n",
            expected_fault_count=1,
            files=(
                RuleFile(
                    path="src/example/support.py",
                    source="def support_value() -> bool:\n    return True\n",
                ),
            ),
        ),
        expected_fault_count=1,
        expected_lines=(1,),
        expected_messages=("all public context zones are available",),
        expected_dependency_paths=("src/example/support.py",),
    ),
    HarnessEvaluationTestCase(
        description="support files are project context rather than direct evaluation targets",
        rule=always_fault,
        rule_case=RuleCase(
            description="primary target only",
            source="PRIMARY = 1\n",
            expected_fault_count=1,
            files=(RuleFile(path="src/example/support.py", source="SUPPORT = 2\n"),),
        ),
        expected_fault_count=1,
        expected_lines=(1,),
        expected_messages=("one direct target",),
    ),
    HarnessEvaluationTestCase(
        description="root scope role and config fragment reach ordinary context policy",
        rule=context_policy,
        rule_case=RuleCase(
            description="root policy context",
            source="VALUE = 1\n",
            expected_fault_count=1,
            path="src/example/main/run.py",
            scope="root",
            scope_root="src/example",
            config={
                "thresholds": {"max_statements": 7},
                "contracts": {"inspect_*": "returns-bool"},
            },
        ),
        expected_fault_count=1,
        expected_lines=(None,),
        expected_messages=("root|main|7|returns-bool|src/example",),
    ),
    HarnessEvaluationTestCase(
        description="test scope and explicit scope root drive discovery position",
        rule=context_policy,
        rule_case=RuleCase(
            description="test policy context",
            source="VALUE = 1\n",
            expected_fault_count=1,
            path="tests/unit/src/example/main/test_run.py",
            scope="test",
            scope_root="tests",
            config={
                "roles": {"main": {"max_statements": 9}},
                "contracts": {"inspect_*": "returns-bool"},
            },
        ),
        expected_fault_count=1,
        expected_lines=(None,),
        expected_messages=("test|main|9|returns-bool|tests",),
    ),
    HarnessEvaluationTestCase(
        description="tooling scope classifies the configured rules role",
        rule=context_policy,
        rule_case=RuleCase(
            description="tooling policy context",
            source="VALUE = 1\n",
            expected_fault_count=1,
            path="scripts/strata/rules/check_clients.py",
            scope="tooling",
            scope_root="scripts",
            config={"contracts": {"inspect_*": "returns-bool"}},
        ),
        expected_fault_count=1,
        expected_lines=(None,),
        expected_messages=("tooling|rules|40|returns-bool|scripts",),
    ),
    HarnessEvaluationTestCase(
        description="explicit scope root disambiguates a nested nonstandard product layout",
        rule=context_policy,
        rule_case=RuleCase(
            description="ambiguous product root",
            source="VALUE = 1\n",
            expected_fault_count=1,
            path="workspace/product/main/run.py",
            scope="root",
            scope_root="workspace/product",
            config={"contracts": {"inspect_*": "returns-bool"}},
        ),
        expected_fault_count=1,
        expected_lines=(None,),
        expected_messages=("root|main|40|returns-bool|workspace/product",),
    ),
    HarnessEvaluationTestCase(
        description="ordinary evaluation sorts rule findings deterministically",
        rule=ordinary_ordering,
        rule_case=RuleCase(
            description="reverse emitted findings",
            source="FIRST = 1\nSECOND = 2\n",
            expected_fault_count=2,
        ),
        expected_fault_count=2,
        expected_lines=(1, 2),
        expected_messages=("ordinary ordering", "ordinary ordering"),
    ),
    HarnessEvaluationTestCase(
        description="internal RuleSpec remains accepted without becoming a top-level export",
        rule=getattr_static(always_fault, _RULE_SPEC_ATTRIBUTE),
        rule_case=RuleCase(
            description="internal compiled spec",
            source="VALUE = 1\n",
            expected_fault_count=1,
        ),
        expected_fault_count=1,
        expected_lines=(1,),
        expected_messages=("one direct target",),
    ),
    HarnessEvaluationTestCase(
        description="ordinary configured exceptions suppress primary findings",
        rule=always_fault,
        rule_case=RuleCase(
            description="file exception",
            source="VALUE = 1\n",
            expected_fault_count=0,
            config={
                "rule_exceptions": [
                    {
                        "rule": "XHT002",
                        "path": "src/example/main/example.py",
                        "reason": "Harness exception behavior.",
                    }
                ]
            },
        ),
        expected_fault_count=0,
        expected_lines=(),
        expected_messages=(),
    ),
    *_FACT_FAMILY_CASES,
)

MISUSE_CASES: tuple[HarnessMisuseTestCase, ...] = (
    HarnessMisuseTestCase(
        description="undecorated functions are rejected",
        rule=undecorated_rule,
        rule_case=RuleCase(
            description="invalid rule", source="VALUE = 1\n", expected_fault_count=0
        ),
        expected_error_type=RuleDefinitionError,
        expected_error_fragment="must be decorated",
    ),
    HarnessMisuseTestCase(
        description="arbitrary rule objects are rejected",
        rule=object(),
        rule_case=RuleCase(
            description="invalid object", source="VALUE = 1\n", expected_fault_count=0
        ),
        expected_error_type=RuleDefinitionError,
        expected_error_fragment="RuleSpec or a function",
    ),
    HarnessMisuseTestCase(
        description="empty descriptions are rejected",
        rule=always_fault,
        rule_case=RuleCase(description=" ", source="VALUE = 1\n", expected_fault_count=0),
        expected_error_type=RuleHarnessError,
        expected_error_fragment="description",
    ),
    HarnessMisuseTestCase(
        description="boolean expected counts are rejected",
        rule=always_fault,
        rule_case=RuleCase(
            description="boolean count",
            source="VALUE = 1\n",
            expected_fault_count=cast(Any, True),
        ),
        expected_error_type=RuleHarnessError,
        expected_error_fragment="non-negative integer",
    ),
    HarnessMisuseTestCase(
        description="negative expected counts are rejected",
        rule=always_fault,
        rule_case=RuleCase(description="negative", source="VALUE = 1\n", expected_fault_count=-1),
        expected_error_type=RuleHarnessError,
        expected_error_fragment="non-negative integer",
    ),
    HarnessMisuseTestCase(
        description="unsupported scopes are rejected",
        rule=always_fault,
        rule_case=RuleCase(
            description="scope",
            source="VALUE = 1\n",
            expected_fault_count=0,
            scope="external",
        ),
        expected_error_type=RuleHarnessError,
        expected_error_fragment="scope must be one of",
    ),
    HarnessMisuseTestCase(
        description="absolute paths are rejected",
        rule=always_fault,
        rule_case=RuleCase(
            description="absolute",
            source="VALUE = 1\n",
            expected_fault_count=0,
            path="/src/example.py",
        ),
        expected_error_type=RuleHarnessError,
        expected_error_fragment="repository-relative POSIX path",
    ),
    HarnessMisuseTestCase(
        description="path traversal is rejected",
        rule=always_fault,
        rule_case=RuleCase(
            description="traversal",
            source="VALUE = 1\n",
            expected_fault_count=0,
            path="src/example/../escape.py",
        ),
        expected_error_type=RuleHarnessError,
        expected_error_fragment="repository-relative POSIX path",
    ),
    HarnessMisuseTestCase(
        description="non-Python paths are rejected",
        rule=always_fault,
        rule_case=RuleCase(
            description="suffix",
            source="VALUE = 1\n",
            expected_fault_count=0,
            path="src/example/main.txt",
        ),
        expected_error_type=RuleHarnessError,
        expected_error_fragment="must end in .py",
    ),
    HarnessMisuseTestCase(
        description="scope roots must contain the primary path",
        rule=always_fault,
        rule_case=RuleCase(
            description="scope root",
            source="VALUE = 1\n",
            expected_fault_count=0,
            scope_root="lib/example",
        ),
        expected_error_type=RuleHarnessError,
        expected_error_fragment="contained by scope_root",
    ),
    HarnessMisuseTestCase(
        description="primary and support path collisions are rejected",
        rule=always_fault,
        rule_case=RuleCase(
            description="collision",
            source="VALUE = 1\n",
            expected_fault_count=0,
            files=(RuleFile(path="src/example/main/example.py", source="OTHER = 2\n"),),
        ),
        expected_error_type=RuleHarnessError,
        expected_error_fragment="collides with the primary",
    ),
    HarnessMisuseTestCase(
        description="duplicate support paths are rejected",
        rule=always_fault,
        rule_case=RuleCase(
            description="duplicate",
            source="VALUE = 1\n",
            expected_fault_count=0,
            files=(
                RuleFile(path="src/example/support.py", source="FIRST = 1\n"),
                RuleFile(path="src/example/support.py", source="SECOND = 2\n"),
            ),
        ),
        expected_error_type=RuleHarnessError,
        expected_error_fragment="Duplicate RuleFile path",
    ),
    HarnessMisuseTestCase(
        description="selection config cannot replace the primary-only ruleset",
        rule=always_fault,
        rule_case=RuleCase(
            description="selection",
            source="VALUE = 1\n",
            expected_fault_count=0,
            config={"select": ["SF"]},
        ),
        expected_error_type=RuleHarnessError,
        expected_error_fragment="harness-owned or unsupported key(s): select",
    ),
    HarnessMisuseTestCase(
        description="evaluation config cannot replace the primary include",
        rule=always_fault,
        rule_case=RuleCase(
            description="evaluation",
            source="VALUE = 1\n",
            expected_fault_count=0,
            config={"evaluation": {"include": ["src/**/*.py"]}},
        ),
        expected_error_type=RuleHarnessError,
        expected_error_fragment="harness-owned or unsupported key(s): evaluation",
    ),
    HarnessMisuseTestCase(
        description="cache config is rejected because the harness uses direct evaluation",
        rule=always_fault,
        rule_case=RuleCase(
            description="cache",
            source="VALUE = 1\n",
            expected_fault_count=0,
            config={"cache": {"enabled": True}},
        ),
        expected_error_type=RuleHarnessError,
        expected_error_fragment="harness-owned or unsupported key(s): cache",
    ),
    HarnessMisuseTestCase(
        description="custom loading config is rejected because the rule object is explicit",
        rule=always_fault,
        rule_case=RuleCase(
            description="loading",
            source="VALUE = 1\n",
            expected_fault_count=0,
            config={"rule_paths": ["rules.py"]},
        ),
        expected_error_type=RuleHarnessError,
        expected_error_fragment="harness-owned or unsupported key(s): rule_paths",
    ),
)


@pytest.mark.parametrize(
    "test_case",
    [HarnessEvaluationTestCase(**vars(test_case)) for test_case in EVALUATION_CASES],
    ids=lambda case: case.description,
)
def test_given_rule_case_when_evaluating_rule_then_uses_real_pipeline(
    test_case: HarnessEvaluationTestCase,
) -> None:
    result: RuleResult = evaluate_rule(rule=test_case.rule, test_case=test_case.rule_case)
    dependency_paths: tuple[str, ...] = tuple(
        dependency.dependency.as_posix() for dependency in result.dependencies
    )

    assert result.fault_count == test_case.expected_fault_count
    assert tuple(fault.line for fault in result.faults) == test_case.expected_lines
    assert tuple(fault.message for fault in result.faults) == test_case.expected_messages
    assert all(not fault.path.is_absolute() for fault in result.faults)
    assert all(not dependency.requester.is_absolute() for dependency in result.dependencies)
    assert all(not dependency.query_path.is_absolute() for dependency in result.dependencies)
    assert all(not dependency.dependency.is_absolute() for dependency in result.dependencies)
    assert all(path in dependency_paths for path in test_case.expected_dependency_paths)


@pytest.mark.parametrize(
    "test_case",
    [HarnessEvaluationTestCase(**vars(test_case)) for test_case in _FACT_FAMILY_CASES],
    ids=lambda case: case.description,
)
@pytest.mark.skipif(
    select_fact_backend().backend is FactBackend.PYTHON,
    reason="The Python reference backend requires one CPython parse for fact extraction.",
)
def test_given_fact_only_rule_when_evaluating_then_avoids_python_ast_parse(
    test_case: HarnessEvaluationTestCase,
) -> None:
    OPERATION_COUNTERS.enable()
    result: RuleResult = evaluate_rule(rule=test_case.rule, test_case=test_case.rule_case)
    counts: dict[str, int] = OPERATION_COUNTERS.snapshot()
    OPERATION_COUNTERS.disable()

    assert result.fault_count == test_case.expected_fault_count
    assert counts.get(PARSE_OPERATION, 0) == test_case.expected_python_parse_count


@pytest.mark.parametrize(
    "test_case",
    [
        HarnessEvaluationTestCase(
            description="path-valued dependency answers are repository-relative",
            rule=all_context_zones,
            rule_case=RuleCase(
                description="directory observation paths",
                source="def primary() -> None:\n    pass\n",
                expected_fault_count=1,
                files=(
                    RuleFile(
                        path="src/example/support.py",
                        source="def support_value() -> bool:\n    return True\n",
                    ),
                ),
            ),
            expected_fault_count=1,
            expected_lines=(1,),
            expected_messages=("all public context zones are available",),
            expected_dependency_paths=("src/example/main", "src/example/support.py"),
        )
    ],
    ids=lambda case: case.description,
)
def test_given_path_dependency_answer_when_evaluating_then_remaps_every_observed_path(
    test_case: HarnessEvaluationTestCase,
) -> None:
    result: RuleResult = evaluate_rule(rule=test_case.rule, test_case=test_case.rule_case)
    answer_paths: tuple[Path, ...] = cast(tuple[Path, ...], result.dependencies[-1].answer)

    assert result.fault_count == test_case.expected_fault_count
    assert tuple(sorted(path.as_posix() for path in answer_paths)) == tuple(
        sorted(test_case.expected_dependency_paths)
    )
    assert all(not path.is_absolute() for path in answer_paths)


@pytest.mark.parametrize(
    "test_case",
    [HarnessMisuseTestCase(**vars(test_case)) for test_case in MISUSE_CASES],
    ids=lambda case: case.description,
)
def test_given_invalid_harness_input_when_evaluating_then_raises_stable_error(
    test_case: HarnessMisuseTestCase,
) -> None:
    with pytest.raises(
        test_case.expected_error_type,
        match=re.escape(test_case.expected_error_fragment),
    ):
        evaluate_rule(rule=test_case.rule, test_case=test_case.rule_case)


@pytest.mark.parametrize(
    "test_case",
    [
        FrozenHarnessModelTestCase(
            description="RuleFile is frozen",
            model=RuleFile(path="src/example/support.py", source="VALUE = 1\n"),
            field_name="path",
            expected_error_type=FrozenInstanceError,
        ),
        FrozenHarnessModelTestCase(
            description="RuleCase is frozen",
            model=RuleCase(description="frozen", source="VALUE = 1\n", expected_fault_count=0),
            field_name="source",
            expected_error_type=FrozenInstanceError,
        ),
        FrozenHarnessModelTestCase(
            description="RuleResult is frozen",
            model=RuleResult(faults=(), dependencies=()),
            field_name="faults",
            expected_error_type=FrozenInstanceError,
        ),
    ],
    ids=lambda case: case.description,
)
def test_given_public_harness_model_when_assigning_field_then_model_is_frozen(
    test_case: FrozenHarnessModelTestCase,
) -> None:
    with pytest.raises(test_case.expected_error_type):
        setattr(test_case.model, test_case.field_name, Path("changed.py"))
