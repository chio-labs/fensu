"""Tests for evaluation AST helper surface."""

from __future__ import annotations

import ast
from collections.abc import Callable, Iterator
from pathlib import Path

import pytest

from strata.analysis.main.build import build_analysis
from strata.analysis.types import AnalysisBuild
from strata.evaluation.helpers import ast_access
from tests.unit.src.strata.evaluation._test_types import (
    AstAccessTestCase,
    AstIndexTestCase,
    CoreWalkTestCase,
)
from tests.unit.src.strata.evaluation.helpers import direct_module_walk_paths


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

    build: AnalysisBuild = build_analysis(
        path=Path("module.py"), source=test_case.source, module=module
    )

    assert len(build.node_index[ast.Call]) == test_case.expected_call_count
    assert ast_access.distinct_callees(fn) == test_case.expected_distinct_callees
    assert ast_access.assigned_locals(fn) == test_case.expected_assigned_locals
    assert ast_access.parameter_names(fn) == test_case.expected_parameter_names
    assert len(ast_access.non_docstring_body(module)) == 1


@pytest.mark.parametrize(
    "test_case",
    [
        AstIndexTestCase(
            description="node and parent indexes share one child traversal",
            source="def run(value: int) -> int:\n    return transform(value)\n",
            expected_node_count=14,
            expected_parent_count=10,
            expected_child_scan_count=14,
        )
    ],
    ids=lambda case: case.description,
)
def test_given_module_when_building_indexes_then_visits_each_node_once(
    monkeypatch: pytest.MonkeyPatch,
    test_case: AstIndexTestCase,
) -> None:
    module: ast.Module = ast.parse(test_case.source)
    original_iter_child_nodes: Callable[[ast.AST], Iterator[ast.AST]] = ast.iter_child_nodes
    child_scan_counts: list[int] = [0]

    def count_child_scan(node: ast.AST) -> tuple[ast.AST, ...]:
        child_scan_counts[0] += 1
        return tuple(original_iter_child_nodes(node))

    monkeypatch.setattr(ast, "iter_child_nodes", count_child_scan)

    build: AnalysisBuild = build_analysis(
        path=Path("module.py"), source=test_case.source, module=module
    )

    assert sum(len(nodes) for nodes in build.node_index.values()) == test_case.expected_node_count
    assert len(build.parent_by_node) == test_case.expected_parent_count
    assert child_scan_counts[0] == test_case.expected_child_scan_count


@pytest.mark.parametrize(
    "test_case",
    [
        CoreWalkTestCase(
            description="core rules delegate all holistic module walks to analysis",
            expected_paths=(),
        )
    ],
    ids=lambda case: case.description,
)
def test_given_core_rules_when_inspecting_walks_then_only_holistic_analysis_walks_module(
    test_case: CoreWalkTestCase,
) -> None:
    direct_walk_paths: tuple[str, ...] = direct_module_walk_paths(root=Path("src/strata/rules"))

    assert direct_walk_paths == test_case.expected_paths
