"""Tests for evaluation AST helper surface."""

from __future__ import annotations

import ast

import pytest

from strata.evaluation.core.helpers import ast_access
from tests.unit.src.strata.evaluation.core._test_types import AstAccessTestCase


@pytest.mark.parametrize(
    "test_case",
    [
        AstAccessTestCase(
            description="helper functions expose calls assignments and parameters",
            source=(
                '"doc"\n'
                "def build(value: int, *items: int, flag: bool = False, **kwargs: int) -> None:\n"
                "    local: int = transform(value)\n"
                "    other: int = pkg.make(local)\n"
                "    return None\n"
            ),
            expected_call_count=2,
            expected_distinct_callees=frozenset({"transform", "pkg.make"}),
            expected_assigned_locals=frozenset({"local", "other"}),
            expected_parameter_names=frozenset({"value", "items", "flag", "kwargs"}),
        )
    ],
    ids=lambda case: case.description,
)
def test_given_module_when_reading_ast_helpers_then_returns_expected_facts(
    test_case: AstAccessTestCase,
) -> None:
    module: ast.Module = ast.parse(test_case.source)
    fn: ast.AST = ast_access.top_level_functions(module)[0]

    assert len(ast_access.build_node_index(module)[ast.Call]) == test_case.expected_call_count
    assert ast_access.distinct_callees(fn) == test_case.expected_distinct_callees
    assert ast_access.assigned_locals(fn) == test_case.expected_assigned_locals
    assert ast_access.parameter_names(fn) == test_case.expected_parameter_names
    assert len(ast_access.non_docstring_body(module)) == 1
