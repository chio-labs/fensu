"""Tests for the backend-neutral Python reference analysis."""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

from strata.analysis.core.exceptions import AnalysisLookupError
from strata.analysis.core.main.build import build_analysis
from strata.analysis.core.models import (
    NodeId,
    OuterStateMutationFact,
    SourceRange,
    SyntaxHandle,
)
from strata.analysis.core.types import Analysis, AnalysisBuild
from tests.unit.src.strata.analysis.core._test_types import (
    AnalysisErrorTestCase,
    OuterStateFactTestCase,
    SourceAnalysisTestCase,
)


@pytest.mark.parametrize(
    "test_case",
    [
        OuterStateFactTestCase(
            description="outer state mutation exposes a backend-neutral source location",
            source="CACHE: list[int] = []\n\ndef run() -> None:\n    CACHE.append(1)\n",
            expected_fact_count=1,
            expected_line=4,
            expected_text="CACHE.append(1)",
        )
    ],
    ids=lambda case: case.description,
)
def test_given_outer_mutation_when_querying_facts_then_returns_exact_location(
    tmp_path: Path,
    test_case: OuterStateFactTestCase,
) -> None:
    path: Path = tmp_path / "module.py"
    analysis: Analysis = build_analysis(
        path=path,
        source=test_case.source,
        module=ast.parse(test_case.source),
    ).analysis

    facts: tuple[OuterStateMutationFact, ...] = analysis.facts.outer_state_mutations()

    assert len(facts) == test_case.expected_fact_count
    assert facts[0].location.start.line == test_case.expected_line
    assert analysis.text.slice(facts[0].location) == test_case.expected_text


@pytest.mark.parametrize(
    "test_case",
    [
        SourceAnalysisTestCase(
            description="unicode source preserves byte locations text and syntax ancestry",
            source="def run() -> None:\n    é = call()\n",
            selected_kind="Call",
            expected_text="call()",
            expected_line=2,
            expected_column=9,
            expected_ancestor_kinds=("Assign", "FunctionDef", "Module"),
        )
    ],
    ids=lambda case: case.description,
)
def test_given_source_when_building_analysis_then_exposes_backend_neutral_queries(
    tmp_path: Path,
    test_case: SourceAnalysisTestCase,
) -> None:
    path: Path = tmp_path / "module.py"
    build: AnalysisBuild = build_analysis(
        path=path,
        source=test_case.source,
        module=ast.parse(test_case.source),
    )
    analysis: Analysis = build.analysis
    handle: SyntaxHandle = analysis.syntax.handles(kind=test_case.selected_kind)[0]
    source_range: SourceRange = analysis.syntax.range(handle)
    ancestor_kinds: tuple[str, ...] = tuple(
        analysis.syntax.kind(ancestor) for ancestor in analysis.relations.ancestors(handle)
    )

    assert analysis.text.slice(source_range) == test_case.expected_text
    assert analysis.text.line(source_range.start.line) == test_case.source.splitlines()[1]
    assert source_range.start.line == test_case.expected_line
    assert source_range.start.column == test_case.expected_column
    assert ancestor_kinds == test_case.expected_ancestor_kinds


@pytest.mark.parametrize(
    "test_case",
    [
        AnalysisErrorTestCase(
            description="foreign syntax handle is rejected",
            source="value = 1\n",
            expected_error_type=AnalysisLookupError,
        )
    ],
    ids=lambda case: case.description,
)
def test_given_foreign_handle_when_querying_analysis_then_raises_lookup_error(
    tmp_path: Path,
    test_case: AnalysisErrorTestCase,
) -> None:
    path: Path = tmp_path / "module.py"
    analysis: Analysis = build_analysis(
        path=path,
        source=test_case.source,
        module=ast.parse(test_case.source),
    ).analysis
    foreign_handle: SyntaxHandle = SyntaxHandle(path=tmp_path / "other.py", node_id=NodeId(0))

    with pytest.raises(test_case.expected_error_type):
        analysis.syntax.range(foreign_handle)
