"""Tests for the backend-neutral Python reference analysis."""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

from strata.analysis.core.exceptions import AnalysisLookupError
from strata.analysis.core.main.build import build_analysis
from strata.analysis.core.models import (
    AnnotationFacts,
    CommentFact,
    FunctionConditionalFact,
    FunctionFacts,
    HygieneFacts,
    MeaningfulReturnFact,
    NodeId,
    OuterStateMutationFact,
    ReferenceFacts,
    SourceRange,
    SyntaxHandle,
)
from strata.analysis.core.types import Analysis, AnalysisBuild
from tests.unit.src.strata.analysis.core._test_types import (
    AnalysisErrorTestCase,
    AnnotationFactTestCase,
    CommentFactTestCase,
    FunctionConditionalFactTestCase,
    FunctionMetricFactTestCase,
    HygieneFactTestCase,
    MeaningfulReturnFactTestCase,
    OuterStateFactTestCase,
    ReferenceFactTestCase,
    SourceAnalysisTestCase,
)


@pytest.mark.parametrize(
    "test_case",
    [
        MeaningfulReturnFactTestCase(
            description="meaningful return facts exclude returns owned by nested functions",
            source=(
                "def validate(value: bool) -> int | None:\n"
                "    def nested() -> int:\n"
                "        return 1\n"
                "    if value:\n"
                "        return 2\n"
                "    return None\n"
            ),
            expected_function_names=("validate", "nested"),
            expected_lines=(5, 3),
        )
    ],
    ids=lambda case: case.description,
)
def test_given_function_returns_when_querying_facts_then_preserves_scope_ownership(
    tmp_path: Path,
    test_case: MeaningfulReturnFactTestCase,
) -> None:
    path: Path = tmp_path / "module.py"
    analysis: Analysis = build_analysis(
        path=path,
        source=test_case.source,
        module=ast.parse(test_case.source),
    ).analysis

    facts: tuple[MeaningfulReturnFact, ...] = analysis.facts.meaningful_returns()

    assert tuple(fact.function_name for fact in facts) == test_case.expected_function_names
    assert tuple(fact.location.line for fact in facts) == test_case.expected_lines


@pytest.mark.parametrize(
    "test_case",
    [
        HygieneFactTestCase(
            description="hygiene facts expose all syntax-policy locations",
            source=(
                '"""Summary.\nDetails.\n"""\n'
                "def probe(value: object) -> bool:\n"
                "    assert value\n"
                '    if value == "raw":\n'
                '        raise ValueError("bad")\n'
                "    if value == 2:\n"
                "        return True\n"
                "    try:\n"
                "        return True\n"
                "    except Exception:\n"
                "        return False\n"
            ),
            expected_docstring_lines=(1,),
            expected_raise_lines=(7,),
            expected_assertion_lines=(5,),
            expected_probe_lines=(12,),
            expected_string_lines=(6,),
            expected_numeric_lines=(8,),
        )
    ],
    ids=lambda case: case.description,
)
def test_given_hygiene_syntax_when_querying_facts_then_returns_policy_locations(
    tmp_path: Path,
    test_case: HygieneFactTestCase,
) -> None:
    path: Path = tmp_path / "module.py"
    analysis: Analysis = build_analysis(
        path=path,
        source=test_case.source,
        module=ast.parse(test_case.source),
    ).analysis

    facts: HygieneFacts = analysis.facts.hygiene()

    assert tuple(location.line for location in facts.multiline_docstrings) == (
        test_case.expected_docstring_lines
    )
    assert tuple(location.line for location in facts.raw_builtin_raises) == (
        test_case.expected_raise_lines
    )
    assert (
        tuple(location.line for location in facts.assertions) == test_case.expected_assertion_lines
    )
    assert tuple(location.line for location in facts.swallowed_exception_probes) == (
        test_case.expected_probe_lines
    )
    assert tuple(location.line for location in facts.unnamed_string_decisions) == (
        test_case.expected_string_lines
    )
    assert tuple(location.line for location in facts.magic_numeric_comparisons) == (
        test_case.expected_numeric_lines
    )


@pytest.mark.parametrize(
    "test_case",
    [
        FunctionMetricFactTestCase(
            description="function facts expose reusable structural metrics",
            source=(
                "def run(value: int, *, option: str) -> None:\n"
                "    result = build(value)\n"
                "    other: int = 1\n"
                "    return None\n"
            ),
            expected_names=("run",),
            expected_top_level_names=("run",),
            expected_statement_counts=(3,),
            expected_call_counts=(1,),
            expected_local_counts=(2,),
            expected_parameter_counts=(2,),
            expected_positional_counts=(1,),
        )
    ],
    ids=lambda case: case.description,
)
def test_given_functions_when_querying_facts_then_returns_shared_structural_metrics(
    tmp_path: Path,
    test_case: FunctionMetricFactTestCase,
) -> None:
    path: Path = tmp_path / "module.py"
    analysis: Analysis = build_analysis(
        path=path,
        source=test_case.source,
        module=ast.parse(test_case.source),
    ).analysis

    facts: FunctionFacts = analysis.facts.functions()

    assert tuple(fact.name for fact in facts.functions) == test_case.expected_names
    assert tuple(fact.name for fact in facts.top_level) == test_case.expected_top_level_names
    assert tuple(fact.statement_count for fact in facts.functions) == (
        test_case.expected_statement_counts
    )
    assert tuple(fact.distinct_call_count for fact in facts.functions) == (
        test_case.expected_call_counts
    )
    assert tuple(fact.assigned_local_count for fact in facts.functions) == (
        test_case.expected_local_counts
    )
    assert tuple(fact.parameter_count for fact in facts.functions) == (
        test_case.expected_parameter_counts
    )
    assert tuple(fact.positional_parameter_count for fact in facts.functions) == (
        test_case.expected_positional_counts
    )


@pytest.mark.parametrize(
    "test_case",
    [
        CommentFactTestCase(
            description="comment facts preserve token text and display positions",
            source="value: int = 1  # inline\n# standalone\n",
            expected_texts=("# inline", "# standalone"),
            expected_lines=(1, 2),
            expected_columns=(16, 0),
        )
    ],
    ids=lambda case: case.description,
)
def test_given_source_comments_when_querying_facts_then_returns_token_positions(
    tmp_path: Path,
    test_case: CommentFactTestCase,
) -> None:
    path: Path = tmp_path / "module.py"
    analysis: Analysis = build_analysis(
        path=path,
        source=test_case.source,
        module=ast.parse(test_case.source),
    ).analysis

    facts: tuple[CommentFact, ...] = analysis.facts.comments()

    assert tuple(fact.text for fact in facts) == test_case.expected_texts
    assert tuple(fact.line for fact in facts) == test_case.expected_lines
    assert tuple(fact.column for fact in facts) == test_case.expected_columns


@pytest.mark.parametrize(
    "test_case",
    [
        ReferenceFactTestCase(
            description="reference facts preserve grouped imports and breadth-first events",
            source=(
                "from pkg.domain.helpers import parse as parser\n"
                "import pkg.domain.helpers.format as formatter\n"
                "value = parser._Cursor()\n"
            ),
            expected_import_modules=(("pkg", "domain", "helpers"), ()),
            expected_import_names=(("parse",), ("pkg.domain.helpers.format",)),
            expected_event_types=("ImportFact", "ImportFact", "AttributeReferenceFact"),
            expected_event_lines=(1, 2, 3),
        )
    ],
    ids=lambda case: case.description,
)
def test_given_imports_and_attributes_when_querying_facts_then_preserves_reference_order(
    tmp_path: Path,
    test_case: ReferenceFactTestCase,
) -> None:
    path: Path = tmp_path / "module.py"
    analysis: Analysis = build_analysis(
        path=path,
        source=test_case.source,
        module=ast.parse(test_case.source),
    ).analysis

    facts: ReferenceFacts = analysis.facts.references()
    imported_names: list[tuple[str, ...]] = []
    for fact in facts.imports:
        imported_names.append(tuple(alias.imported_name for alias in fact.aliases))

    assert tuple(fact.module_parts for fact in facts.imports) == test_case.expected_import_modules
    assert tuple(imported_names) == test_case.expected_import_names
    assert tuple(type(event).__name__ for event in facts.events) == test_case.expected_event_types
    assert tuple(event.location.line for event in facts.events) == test_case.expected_event_lines


@pytest.mark.parametrize(
    "test_case",
    [
        FunctionConditionalFactTestCase(
            description="function conditionals expose owner decorators and source order",
            source=(
                "@pytest.mark.parametrize('value', [1])\n"
                "def test_value(value: int) -> None:\n"
                "    selected: int = value if value else 0\n"
                "    filtered: list[int] = [item for item in [value] if item]\n"
            ),
            expected_function_names=("test_value", "test_value"),
            expected_decorator_names=(
                ("pytest.mark.parametrize",),
                ("pytest.mark.parametrize",),
            ),
            expected_lines=(3, 4),
        )
    ],
    ids=lambda case: case.description,
)
def test_given_function_conditionals_when_querying_facts_then_returns_owner_metadata(
    tmp_path: Path,
    test_case: FunctionConditionalFactTestCase,
) -> None:
    path: Path = tmp_path / "module.py"
    analysis: Analysis = build_analysis(
        path=path,
        source=test_case.source,
        module=ast.parse(test_case.source),
    ).analysis

    facts: tuple[FunctionConditionalFact, ...] = analysis.facts.function_conditionals()

    assert tuple(fact.function_name for fact in facts) == test_case.expected_function_names
    assert tuple(fact.decorator_names for fact in facts) == test_case.expected_decorator_names
    assert tuple(fact.location.start.line for fact in facts) == test_case.expected_lines


@pytest.mark.parametrize(
    "test_case",
    [
        AnnotationFactTestCase(
            description="one traversal exposes function and first-local annotation facts",
            source=(
                "class Service:\n"
                "    def run(self, value, *, option: str):\n"
                "        typed: int = 1\n"
                "        typed = 2\n"
                "        local = value\n"
            ),
            expected_parameter_names=("value",),
            expected_parameter_lines=(2,),
            expected_return_names=("run",),
            expected_return_lines=(2,),
            expected_local_names=("local",),
            expected_local_lines=(5,),
        )
    ],
    ids=lambda case: case.description,
)
def test_given_missing_annotations_when_querying_facts_then_returns_all_fact_groups(
    tmp_path: Path,
    test_case: AnnotationFactTestCase,
) -> None:
    path: Path = tmp_path / "module.py"
    analysis: Analysis = build_analysis(
        path=path,
        source=test_case.source,
        module=ast.parse(test_case.source),
    ).analysis

    facts: AnnotationFacts = analysis.facts.annotations()

    assert tuple(fact.name for fact in facts.parameters) == test_case.expected_parameter_names
    assert tuple(fact.location.start.line for fact in facts.parameters) == (
        test_case.expected_parameter_lines
    )
    assert tuple(fact.name for fact in facts.returns) == test_case.expected_return_names
    assert (
        tuple(fact.location.start.line for fact in facts.returns) == test_case.expected_return_lines
    )
    assert tuple(fact.name for fact in facts.locals) == test_case.expected_local_names
    assert (
        tuple(fact.location.start.line for fact in facts.locals) == test_case.expected_local_lines
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
