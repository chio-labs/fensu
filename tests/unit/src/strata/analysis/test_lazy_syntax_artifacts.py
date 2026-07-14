"""Tests for lazily parsed CPython syntax artifacts."""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

from strata.analysis.classes.lazy_syntax_artifacts import LazySyntaxArtifacts
from strata.instrumentation.constants import OPERATION_COUNTERS, PARSE_OPERATION
from tests.unit.src.strata.analysis._test_types import LazyArtifactsTestCase


@pytest.mark.parametrize(
    "test_case",
    [
        LazyArtifactsTestCase(
            description="module access parses the bound source exactly once",
            source="value: int = 1\n",
            provide_module=False,
            accessed_properties=("module", "nodes", "node_index", "parent_by_node"),
            expected_parse_operations=1,
            expected_node_count=7,
        ),
        LazyArtifactsTestCase(
            description="index access alone still triggers exactly one parse",
            source="value: int = 1\n",
            provide_module=False,
            accessed_properties=("node_index",),
            expected_parse_operations=1,
            expected_node_count=7,
        ),
        LazyArtifactsTestCase(
            description="adopted eager module never re-parses",
            source="value: int = 1\n",
            provide_module=True,
            accessed_properties=("module", "nodes", "node_index", "parent_by_node"),
            expected_parse_operations=0,
            expected_node_count=7,
        ),
        LazyArtifactsTestCase(
            description="unaccessed artifacts never parse",
            source="value: int = 1\n",
            provide_module=False,
            accessed_properties=(),
            expected_parse_operations=0,
            expected_node_count=7,
        ),
    ],
    ids=lambda case: case.description,
)
def test_given_source_when_accessing_artifacts_then_parses_only_on_demand(
    test_case: LazyArtifactsTestCase,
) -> None:
    module: ast.Module | None = {
        True: ast.parse(test_case.source),
        False: None,
    }[test_case.provide_module]
    artifacts: LazySyntaxArtifacts = LazySyntaxArtifacts(
        path=Path("module.py"), source=test_case.source, module=module
    )

    OPERATION_COUNTERS.enable()
    for name in test_case.accessed_properties:
        _ = getattr(artifacts, name)
    recorded: int = OPERATION_COUNTERS.snapshot().get(PARSE_OPERATION, 0)
    OPERATION_COUNTERS.disable()

    assert recorded == test_case.expected_parse_operations
    assert len(artifacts.nodes) == test_case.expected_node_count
    assert isinstance(artifacts.module, ast.Module)
