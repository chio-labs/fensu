"""Tests for the backend-neutral Python reference analysis."""

from __future__ import annotations

import ast
from pathlib import Path
from typing import cast

import pytest

from strata.analysis.exceptions import AnalysisLookupError
from strata.analysis.main.build import build_analysis
from strata.analysis.models import (
    AnnotationFacts,
    CommentFact,
    DataclassFact,
    FunctionConditionalFact,
    FunctionContractFact,
    FunctionFacts,
    HygieneFacts,
    MeaningfulReturnFact,
    ModuleDeclarationFacts,
    NodeId,
    OuterStateMutationFact,
    ParameterMutationFact,
    ParametrizeFact,
    ProjectCallFacts,
    ProjectFunctionFact,
    PytestFunctionFact,
    PytestModuleFacts,
    ReferenceFacts,
    SourceRange,
    SyntaxHandle,
)
from strata.analysis.types import Analysis, AnalysisBuild
from tests.unit.src.strata.analysis._test_types import (
    AnalysisErrorTestCase,
    AnnotationFactTestCase,
    CommentFactTestCase,
    DataclassFactTestCase,
    FunctionConditionalFactTestCase,
    FunctionContractFactTestCase,
    FunctionMetricFactTestCase,
    HygieneFactTestCase,
    MeaningfulReturnFactTestCase,
    ModuleDeclarationFactTestCase,
    OuterStateFactTestCase,
    ParameterMutationFactTestCase,
    ProjectCallFactTestCase,
    PytestFunctionFactTestCase,
    PytestModuleFactTestCase,
    ReferenceFactTestCase,
    SourceAnalysisTestCase,
)
from tests.unit.src.strata.analysis.helpers import meaningful_return_lines


@pytest.mark.parametrize(
    "test_case",
    [
        ProjectCallFactTestCase(
            description="project call facts preserve contracts targets shadowing and scope",
            source=(
                "from pkg.phases import load as imported_load\n"
                "import pkg.compile as compile_module\n\n"
                "def local_phase() -> int:\n"
                "    return 1\n\n"
                "def no_result() -> None:\n"
                "    return None\n\n"
                "def run(*, imported_load: object) -> None:\n"
                "    local_phase()\n"
                "    imported_load()\n"
                "    compile_module.compile_project()\n"
                "    def nested() -> None:\n"
                "        local_phase()\n"
            ),
            expected_function_names=("local_phase", "no_result", "run"),
            expected_meaningful_results=(True, False, False),
            expected_module_names=(None, "pkg.compile"),
            expected_call_names=("local_phase", "compile_project"),
            expected_call_lines=(11, 13),
        )
    ],
    ids=lambda case: case.description,
)
def test_given_project_calls_when_querying_facts_then_returns_backend_neutral_targets(
    tmp_path: Path,
    test_case: ProjectCallFactTestCase,
) -> None:
    path: Path = tmp_path / "main.py"
    analysis: Analysis = build_analysis(
        path=path,
        source=test_case.source,
        module=ast.parse(test_case.source),
    ).analysis
    facts: ProjectCallFacts = analysis.facts.project_calls()
    function_facts: tuple[ProjectFunctionFact, ...] = analysis.facts.project_functions()

    assert tuple(fact.name for fact in function_facts) == test_case.expected_function_names
    assert tuple(fact.meaningful_result for fact in function_facts) == (
        test_case.expected_meaningful_results
    )
    assert tuple(fact.module_name for fact in facts.discarded_calls) == (
        test_case.expected_module_names
    )
    assert tuple(fact.function_name for fact in facts.discarded_calls) == (
        test_case.expected_call_names
    )
    assert tuple(fact.location.line for fact in facts.discarded_calls) == (
        test_case.expected_call_lines
    )


@pytest.mark.parametrize(
    "test_case",
    [
        PytestModuleFactTestCase(
            description="test module facts expose declaration shape and ordering",
            source=(
                '"""Module."""\n'
                "from pkg import Value\n\n"
                "def helper() -> None:\n"
                "    pass\n\n"
                "TEST_CASES = []\n\n"
                "def test_given_value_when_checking_then_matches() -> None:\n"
                "    pass\n\n"
                "_LATE = 1\n"
            ),
            expected_empty_or_docstring_only=False,
            expected_scenario_lines=(4, 7, 9, 12),
            expected_helper_lines=(4,),
            expected_case_list_lines=(7,),
            expected_private_lines=(12,),
        )
    ],
    ids=lambda case: case.description,
)
def test_given_test_module_when_querying_facts_then_returns_declaration_shape(
    tmp_path: Path,
    test_case: PytestModuleFactTestCase,
) -> None:
    path: Path = tmp_path / "module.py"
    analysis: Analysis = build_analysis(
        path=path,
        source=test_case.source,
        module=ast.parse(test_case.source),
    ).analysis

    facts: PytestModuleFacts = analysis.facts.test_module()

    assert facts.empty_or_docstring_only is test_case.expected_empty_or_docstring_only
    assert tuple(location.line for location in facts.scenario_invalid_locations) == (
        test_case.expected_scenario_lines
    )
    assert tuple(location.line for location in facts.top_level_helper_locations) == (
        test_case.expected_helper_lines
    )
    assert tuple(location.line for location in facts.test_case_list_locations) == (
        test_case.expected_case_list_lines
    )
    assert tuple(location.line for location in facts.private_after_test_locations) == (
        test_case.expected_private_lines
    )


@pytest.mark.parametrize(
    "test_case",
    [
        PytestFunctionFactTestCase(
            description="test function facts expose parametrization and expected references",
            source=(
                "@pytest.mark.parametrize(\n"
                "    'test_case',\n"
                "    [ExampleTestCase(description='case', expected_value=1)],\n"
                "    ids=lambda case: case.description,\n"
                ")\n"
                "def test_given_value_when_checking_then_matches(\n"
                "    test_case: ExampleTestCase,\n"
                ") -> None:\n"
                "    assert test_case.expected_value == 1\n"
            ),
            expected_names=("test_given_value_when_checking_then_matches",),
            expected_annotations=("ExampleTestCase",),
            expected_parameter_names=("test_case",),
            expected_ids=(True,),
            expected_case_constructors=(("ExampleTestCase",),),
            expected_references=(True,),
        )
    ],
    ids=lambda case: case.description,
)
def test_given_test_functions_when_querying_facts_then_returns_pytest_metadata(
    tmp_path: Path,
    test_case: PytestFunctionFactTestCase,
) -> None:
    path: Path = tmp_path / "module.py"
    analysis: Analysis = build_analysis(
        path=path,
        source=test_case.source,
        module=ast.parse(test_case.source),
    ).analysis

    facts: tuple[PytestFunctionFact, ...] = analysis.facts.test_functions()
    parametrizations: tuple[ParametrizeFact, ...] = tuple(
        cast(ParametrizeFact, fact.parametrize) for fact in facts
    )
    case_constructors: list[tuple[str | None, ...]] = []
    for parametrization in parametrizations:
        case_constructors.append(tuple(case.constructor_name for case in parametrization.cases))

    assert tuple(fact.name for fact in facts) == test_case.expected_names
    assert tuple(fact.test_case_annotation_name for fact in facts) == test_case.expected_annotations
    assert (
        tuple(fact.parameter_name for fact in parametrizations)
        == test_case.expected_parameter_names
    )
    assert tuple(fact.description_lambda_ids for fact in parametrizations) == test_case.expected_ids
    assert tuple(case_constructors) == test_case.expected_case_constructors
    assert tuple(fact.references_expected_field for fact in facts) == test_case.expected_references


@pytest.mark.parametrize(
    "test_case",
    [
        DataclassFactTestCase(
            description="dataclass facts expose fields frozen state and decorator ownership",
            source=(
                "@dataclass(frozen=True)\n"
                "class Case:\n"
                "    description: str\n"
                "    expected_value: int\n\n"
                "@dataclasses.dataclass\n"
                "class External:\n"
                "    value: int\n"
            ),
            expected_names=("Case", "External"),
            expected_field_names=(
                frozenset({"description", "expected_value"}),
                frozenset({"value"}),
            ),
            expected_frozen=(True, False),
            expected_shape_candidates=(True, False),
        )
    ],
    ids=lambda case: case.description,
)
def test_given_dataclass_declarations_when_querying_facts_then_returns_model_metadata(
    tmp_path: Path,
    test_case: DataclassFactTestCase,
) -> None:
    path: Path = tmp_path / "module.py"
    analysis: Analysis = build_analysis(
        path=path,
        source=test_case.source,
        module=ast.parse(test_case.source),
    ).analysis

    facts: tuple[DataclassFact, ...] = analysis.facts.dataclasses()

    assert tuple(fact.name for fact in facts) == test_case.expected_names
    assert tuple(fact.field_names for fact in facts) == test_case.expected_field_names
    assert tuple(fact.frozen for fact in facts) == test_case.expected_frozen
    assert tuple(fact.shape_candidate for fact in facts) == test_case.expected_shape_candidates


@pytest.mark.parametrize(
    "test_case",
    [
        ModuleDeclarationFactTestCase(
            description="module declaration facts classify top-level and nested classes",
            source=(
                '"""Module."""\n'
                "import pkg\n\n"
                "@dataclass\n"
                "class Result:\n"
                "    value: int\n\n"
                "class ProblemError(Exception):\n"
                "    pass\n\n"
                "def build() -> None:\n"
                "    class NestedError(Exception):\n"
                "        pass\n\n"
                "class Service(Protocol):\n"
                "    pass\n\n"
                "DEFAULT_VALUE: int = 1\n"
                "PathMode: TypeAlias = str\n"
            ),
            expected_statement_lines=(2, 5, 8, 11, 15, 18, 19),
            expected_model_flags=(False, True, False, False, False, False, False),
            expected_exception_flags=(False, False, True, False, False, False, False),
            expected_model_lines=(5,),
            expected_type_lines=(15, 19),
            expected_exception_lines=(8, 12),
            expected_assignment_names=((), (), (), (), (), ("DEFAULT_VALUE",), ("PathMode",)),
        )
    ],
    ids=lambda case: case.description,
)
def test_given_module_declarations_when_querying_facts_then_returns_role_classifications(
    tmp_path: Path,
    test_case: ModuleDeclarationFactTestCase,
) -> None:
    path: Path = tmp_path / "module.py"
    analysis: Analysis = build_analysis(
        path=path,
        source=test_case.source,
        module=ast.parse(test_case.source),
    ).analysis

    facts: ModuleDeclarationFacts = analysis.facts.module_declarations()

    assert tuple(fact.location.line for fact in facts.statements) == (
        test_case.expected_statement_lines
    )
    assert tuple(fact.model_class for fact in facts.statements) == test_case.expected_model_flags
    assert tuple(fact.exception_class for fact in facts.statements) == (
        test_case.expected_exception_flags
    )
    assert (
        tuple(location.line for location in facts.model_locations) == test_case.expected_model_lines
    )
    assert tuple(fact.location.line for fact in facts.type_declarations) == (
        test_case.expected_type_lines
    )
    assert tuple(location.line for location in facts.exception_locations) == (
        test_case.expected_exception_lines
    )
    assert tuple(fact.assignment_target_names for fact in facts.statements) == (
        test_case.expected_assignment_names
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
            expected_function_names=("validate",),
            expected_lines=(5,),
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

    facts: tuple[MeaningfulReturnFact, ...] = analysis.facts.meaningful_returns(
        name_patterns=("validate*",)
    )

    assert tuple(fact.function_name for fact in facts) == test_case.expected_function_names
    assert tuple(fact.location.line for fact in facts) == test_case.expected_lines


@pytest.mark.parametrize(
    "test_case",
    [
        FunctionContractFactTestCase(
            description="contract facts normalize annotations and preserve owned body boundaries",
            source=(
                "def is_ready() -> 'typing.TypeGuard[int]':\n    return True\n"
                "def iter_rows() -> Iterable[int]:\n"
                "    def nested():\n        yield 0\n"
                "    yield 1\n"
                "async def get_value():\n    return None\n"
            ),
            expected_function_names=("is_ready", "iter_rows", "nested", "get_value"),
            expected_categories=("type-guard", "other", "missing", "missing"),
            expected_annotations=("typing.TypeGuard[int]", "Iterable[int]", "missing", "missing"),
            expected_contains_yield=(False, True, True, False),
            expected_meaningful_return_lines=(2, None, None, None),
        )
    ],
    ids=lambda case: case.description,
)
def test_given_function_contracts_when_querying_facts_then_returns_descriptive_shapes(
    tmp_path: Path,
    test_case: FunctionContractFactTestCase,
) -> None:
    path: Path = tmp_path / "module.py"
    analysis: Analysis = build_analysis(
        path=path,
        source=test_case.source,
        module=ast.parse(test_case.source),
    ).analysis

    facts: tuple[FunctionContractFact, ...] = analysis.facts.function_contracts()

    assert tuple(fact.function_name for fact in facts) == test_case.expected_function_names
    assert tuple(fact.return_annotation_category for fact in facts) == test_case.expected_categories
    assert tuple(fact.return_annotation for fact in facts) == test_case.expected_annotations
    assert tuple(fact.contains_yield for fact in facts) == test_case.expected_contains_yield
    assert meaningful_return_lines(facts) == test_case.expected_meaningful_return_lines


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
                "        scalar = -1\n"
                "        local = value\n"
            ),
            expected_parameter_names=("value",),
            expected_parameter_lines=(2,),
            expected_return_names=("run",),
            expected_return_lines=(2,),
            expected_local_names=("scalar", "local"),
            expected_local_lines=(5, 6),
            expected_local_scalar_literals=(True, False),
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
    assert tuple(fact.location.line for fact in facts.parameters) == (
        test_case.expected_parameter_lines
    )
    assert tuple(fact.name for fact in facts.returns) == test_case.expected_return_names
    assert tuple(fact.location.line for fact in facts.returns) == test_case.expected_return_lines
    assert tuple(fact.name for fact in facts.locals) == test_case.expected_local_names
    assert tuple(fact.location.line for fact in facts.locals) == test_case.expected_local_lines
    assert tuple(fact.scalar_literal for fact in facts.locals) == (
        test_case.expected_local_scalar_literals
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
        ParameterMutationFactTestCase(
            description="parameter mutation facts preserve first locations and return status",
            source=(
                "def update(left: list[int], right: list[int]) -> list[int]:\n"
                "    left.append(1)\n"
                "    left.append(2)\n"
                "    right[0] = 1\n"
                "    return left\n"
            ),
            expected_parameter_names=("right", "left"),
            expected_lines=(4, 2),
            expected_returned=(False, True),
        ),
        ParameterMutationFactTestCase(
            description="nested function mutation is attributed to every parameter owner",
            source=(
                "def outer(values: list[int]) -> None:\n"
                "    def inner(values: list[int]) -> None:\n"
                "        values.append(1)\n"
            ),
            expected_parameter_names=("values", "values"),
            expected_lines=(3, 3),
            expected_returned=(False, False),
        ),
        ParameterMutationFactTestCase(
            description="nested return preserves enclosing function return classification",
            source=(
                "def outer(values: list[int]) -> None:\n"
                "    values.append(1)\n"
                "    def inner() -> list[int]:\n"
                "        return values\n"
            ),
            expected_parameter_names=("values",),
            expected_lines=(2,),
            expected_returned=(True,),
        ),
        ParameterMutationFactTestCase(
            description="lambda body mutation is attributed to its enclosing function",
            source=(
                "def outer(values: list[int]) -> None:\n    mutate = lambda: values.append(1)\n"
            ),
            expected_parameter_names=("values",),
            expected_lines=(2,),
            expected_returned=(False,),
        ),
    ],
    ids=lambda case: case.description,
)
def test_given_parameter_mutations_when_querying_facts_then_returns_first_mutations(
    tmp_path: Path,
    test_case: ParameterMutationFactTestCase,
) -> None:
    path: Path = tmp_path / "module.py"
    analysis: Analysis = build_analysis(
        path=path,
        source=test_case.source,
        module=ast.parse(test_case.source),
    ).analysis

    facts: tuple[ParameterMutationFact, ...] = analysis.facts.parameter_mutations()

    assert tuple(fact.parameter_name for fact in facts) == test_case.expected_parameter_names
    assert tuple(fact.location.line for fact in facts) == test_case.expected_lines
    assert tuple(fact.returned for fact in facts) == test_case.expected_returned


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
