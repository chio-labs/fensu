"""Test case types for backend-neutral source analysis."""

from dataclasses import dataclass


@dataclass(frozen=True)
class ParseValidityTestCase:
    """One source snippet with its expected validity under both parsers."""

    description: str
    source: str
    expected_cpython_valid: bool
    expected_native_valid: bool


@dataclass(frozen=True)
class FactDelegationTestCase:
    """One fact family and the sentinel its delegation must return."""

    description: str
    method_name: str
    expected_sentinel: str


@dataclass(frozen=True)
class FactBackendSelectionTestCase:
    """Environment and availability state with the expected selection result."""

    description: str
    requested_value: str | None
    native_available: bool
    expected_backend: str
    expected_native_version: str | None
    expected_warning_present: bool


@dataclass(frozen=True)
class PythonSourceFactoryTestCase:
    """Exact source bytes and expected normalized analysis artifact."""

    description: str
    content: bytes
    expected_source: str
    expected_fingerprint: str
    expected_assignment_count: int


@dataclass(frozen=True)
class PythonSourceFactoryErrorTestCase:
    """Invalid source bytes and expected structured failure."""

    description: str
    content: bytes
    expected_error_type: type[Exception]
    expected_message: str | None
    expected_line: int | None
    expected_column: int | None


@dataclass(frozen=True)
class PythonSourceFactoryOperationTestCase:
    """Expected parse and fingerprint operation counts."""

    description: str
    content: bytes
    source_fingerprint: str | None
    expected_fingerprint: str
    expected_parse_count: int
    expected_hash_count: int


@dataclass(frozen=True)
class SourceAnalysisTestCase:
    """Source and expected syntax, relation, and text facts."""

    description: str
    source: str
    selected_kind: str
    expected_text: str
    expected_line: int
    expected_column: int
    expected_ancestor_kinds: tuple[str, ...]


@dataclass(frozen=True)
class AnalysisErrorTestCase:
    """Source and expected analysis query error."""

    description: str
    source: str
    expected_error_type: type[Exception]


@dataclass(frozen=True)
class OuterStateFactTestCase:
    """Source and expected backend-neutral outer-state mutation fact."""

    description: str
    source: str
    expected_fact_count: int
    expected_line: int
    expected_text: str


@dataclass(frozen=True)
class ParameterMutationFactTestCase:
    """Source and expected backend-neutral parameter mutation facts."""

    description: str
    source: str
    expected_parameter_names: tuple[str, ...]
    expected_lines: tuple[int, ...]
    expected_returned: tuple[bool, ...]


@dataclass(frozen=True)
class AnnotationFactTestCase:
    """Source and expected shared missing-annotation facts."""

    description: str
    source: str
    expected_parameter_names: tuple[str, ...]
    expected_parameter_lines: tuple[int, ...]
    expected_return_names: tuple[str, ...]
    expected_return_lines: tuple[int, ...]
    expected_local_names: tuple[str, ...]
    expected_local_lines: tuple[int, ...]
    expected_local_scalar_literals: tuple[bool, ...]


@dataclass(frozen=True)
class FunctionConditionalFactTestCase:
    """Source and expected function conditional-control-flow facts."""

    description: str
    source: str
    expected_function_names: tuple[str, ...]
    expected_decorator_names: tuple[tuple[str, ...], ...]
    expected_lines: tuple[int, ...]


@dataclass(frozen=True)
class ReferenceFactTestCase:
    """Source and expected import and attribute-reference facts."""

    description: str
    source: str
    expected_import_modules: tuple[tuple[str, ...], ...]
    expected_import_names: tuple[tuple[str, ...], ...]
    expected_event_types: tuple[str, ...]
    expected_event_lines: tuple[int, ...]


@dataclass(frozen=True)
class CommentFactTestCase:
    """Source and expected tokenized comment facts."""

    description: str
    source: str
    expected_texts: tuple[str, ...]
    expected_lines: tuple[int, ...]
    expected_columns: tuple[int, ...]


@dataclass(frozen=True)
class FunctionMetricFactTestCase:
    """Source and expected shared structural function metrics."""

    description: str
    source: str
    expected_names: tuple[str, ...]
    expected_top_level_names: tuple[str, ...]
    expected_statement_counts: tuple[int, ...]
    expected_call_counts: tuple[int, ...]
    expected_local_counts: tuple[int, ...]
    expected_parameter_counts: tuple[int, ...]
    expected_positional_counts: tuple[int, ...]


@dataclass(frozen=True)
class ProjectCallFactTestCase:
    """Source and expected project-call contracts and discarded targets."""

    description: str
    source: str
    expected_function_names: tuple[str, ...]
    expected_meaningful_results: tuple[bool, ...]
    expected_module_names: tuple[str | None, ...]
    expected_call_names: tuple[str, ...]
    expected_call_lines: tuple[int, ...]


@dataclass(frozen=True)
class MeaningfulReturnFactTestCase:
    """Source and expected owned meaningful-return facts."""

    description: str
    source: str
    expected_function_names: tuple[str, ...]
    expected_lines: tuple[int, ...]


@dataclass(frozen=True)
class FunctionContractFactTestCase:
    """Source and expected descriptive function contract facts."""

    description: str
    source: str
    expected_function_names: tuple[str, ...]
    expected_categories: tuple[str, ...]
    expected_annotations: tuple[str, ...]
    expected_contains_yield: tuple[bool, ...]
    expected_meaningful_return_lines: tuple[int | None, ...]


@dataclass(frozen=True)
class HygieneFactTestCase:
    """Source and expected syntax-based hygiene fact locations."""

    description: str
    source: str
    expected_docstring_lines: tuple[int, ...]
    expected_raise_lines: tuple[int, ...]
    expected_assertion_lines: tuple[int, ...]
    expected_probe_lines: tuple[int, ...]
    expected_string_lines: tuple[int, ...]
    expected_numeric_lines: tuple[int, ...]


@dataclass(frozen=True)
class DataclassFactTestCase:
    """Source and expected top-level dataclass metadata."""

    description: str
    source: str
    expected_names: tuple[str, ...]
    expected_field_names: tuple[frozenset[str], ...]
    expected_frozen: tuple[bool, ...]
    expected_shape_candidates: tuple[bool, ...]


@dataclass(frozen=True)
class ModuleDeclarationFactTestCase:
    """Source and expected module-role declaration facts."""

    description: str
    source: str
    expected_statement_lines: tuple[int, ...]
    expected_model_flags: tuple[bool, ...]
    expected_exception_flags: tuple[bool, ...]
    expected_model_lines: tuple[int, ...]
    expected_type_lines: tuple[int, ...]
    expected_exception_lines: tuple[int, ...]
    expected_assignment_names: tuple[tuple[str, ...], ...]


@dataclass(frozen=True)
class PytestFunctionFactTestCase:
    """Source and expected pytest function metadata."""

    description: str
    source: str
    expected_names: tuple[str, ...]
    expected_annotations: tuple[str | None, ...]
    expected_parameter_names: tuple[str | None, ...]
    expected_ids: tuple[bool, ...]
    expected_case_constructors: tuple[tuple[str | None, ...], ...]
    expected_references: tuple[bool, ...]


@dataclass(frozen=True)
class HarnessUseFactTestCase:
    """Source and expected static evaluate_rule harness facts."""

    description: str
    source: str
    expected_singular_parameter: str | None
    expected_dimension_parameters: tuple[tuple[str, ...], ...]
    expected_dimension_case_counts: tuple[int, ...]
    expected_dimension_unknown: tuple[bool, ...]
    expected_call_lines: tuple[int, ...]
    expected_owner_names: tuple[str | None, ...]
    expected_rule_references: tuple[tuple[str | None, str | None], ...]
    expected_forms: tuple[str, ...]
    expected_case_counts: tuple[int, ...]
    expected_case_lines: tuple[tuple[int, ...], ...]
    expected_unknown: tuple[bool, ...]


@dataclass(frozen=True)
class HarnessUseFactMatrixTestCase:
    """Static harness fact scenarios exercised as one visible pytest case."""

    description: str
    cases: tuple[HarnessUseFactTestCase, ...]
    expected_case_count: int


@dataclass(frozen=True)
class RuleTestAssociationFactTestCase:
    """Harness calls, module analyses, and expected resolved associations."""

    description: str
    test_source: str
    module_names: tuple[str, ...]
    module_sources: tuple[str, ...]
    expected_rule_references: tuple[tuple[str, str], ...]
    expected_case_counts: tuple[int, ...]
    expected_call_counts: tuple[int, ...]
    expected_unknown: tuple[bool, ...]


@dataclass(frozen=True)
class RuleTestAssociationFactMatrixTestCase:
    """Rule association scenarios exercised as one visible pytest case."""

    description: str
    cases: tuple[RuleTestAssociationFactTestCase, ...]
    expected_case_count: int


@dataclass(frozen=True)
class PytestConditionalFactTestCase:
    """Source and expected conditional locations for test functions."""

    description: str
    source: str
    expected_lines: tuple[int, ...]


@dataclass(frozen=True)
class ObserverFingerprintParityTestCase:
    """Source bytes and expected fingerprint parity across implementations."""

    description: str
    source: bytes
    expected_available: bool


@dataclass(frozen=True)
class ObserverQueryTestCase:
    """One small layout and expected shared observation answers."""

    description: str
    file_names: tuple[str, ...]
    directory_names: tuple[str, ...]
    glob_pattern: str
    glob_recursive: bool
    expected_entry_names: tuple[str, ...]
    expected_glob_names: tuple[str, ...]
    expected_missing_source: bool


@dataclass(frozen=True)
class PytestModuleFactTestCase:
    """Source and expected test module-shape metadata."""

    description: str
    source: str
    expected_empty_or_docstring_only: bool
    expected_scenario_lines: tuple[int, ...]
    expected_helper_lines: tuple[int, ...]
    expected_case_list_lines: tuple[int, ...]
    expected_private_lines: tuple[int, ...]
