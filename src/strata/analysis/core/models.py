"""Backend-neutral source identity and location models."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class NodeId:
    """An opaque syntax identity unique within one analyzed file."""

    value: int


@dataclass(frozen=True, slots=True)
class SyntaxHandle:
    """A file-qualified opaque reference to one syntax node."""

    path: Path
    node_id: NodeId


@dataclass(frozen=True, slots=True, order=True)
class SourcePosition:
    """A one-based line and zero-based UTF-8 byte column and offset."""

    line: int
    column: int
    offset: int


@dataclass(frozen=True, slots=True)
class SourceRange:
    """An end-exclusive source range within one file."""

    path: Path
    start: SourcePosition
    end: SourcePosition


@dataclass(frozen=True, slots=True)
class SourceLocation:
    """A file and one-based line with zero-based diagnostic column."""

    path: Path
    line: int
    column: int


@dataclass(frozen=True, slots=True)
class OuterStateMutationFact:
    """A direct mutation resolving to module or enclosing-function state."""

    location: SourceRange


@dataclass(frozen=True, slots=True)
class MissingParameterAnnotationFact:
    """A function parameter requiring an annotation."""

    name: str
    location: SourceLocation


@dataclass(frozen=True, slots=True)
class MissingReturnAnnotationFact:
    """A function requiring a return annotation."""

    name: str
    location: SourceLocation


@dataclass(frozen=True, slots=True)
class MissingLocalAnnotationFact:
    """A first local binding requiring an annotation."""

    name: str
    location: SourceLocation


@dataclass(frozen=True, slots=True)
class MissingVariableAnnotationFact:
    """An unannotated module variable or class attribute."""

    name: str
    location: SourceLocation


@dataclass(frozen=True, slots=True)
class AnnotationFacts:
    """Missing annotation facts collected by one shared file traversal."""

    parameters: tuple[MissingParameterAnnotationFact, ...]
    returns: tuple[MissingReturnAnnotationFact, ...]
    locals: tuple[MissingLocalAnnotationFact, ...]
    module_variables: tuple[MissingVariableAnnotationFact, ...]
    class_attributes: tuple[MissingVariableAnnotationFact, ...]


@dataclass(frozen=True, slots=True)
class FunctionConditionalFact:
    """Conditional control flow owned by a function."""

    function_name: str
    decorator_names: tuple[str, ...]
    location: SourceRange


@dataclass(frozen=True, slots=True)
class ImportAliasFact:
    """One imported name and its local binding."""

    imported_name: str
    imported_parts: tuple[str, ...]
    bound_name: str


@dataclass(frozen=True, slots=True)
class ImportFact:
    """One import statement and its imported names."""

    location: SourceLocation
    module_parts: tuple[str, ...]
    aliases: tuple[ImportAliasFact, ...]
    relative_level: int
    from_import: bool
    top_level: bool


@dataclass(frozen=True, slots=True)
class AttributeReferenceFact:
    """One attribute reference and its leftmost base name."""

    location: SourceLocation
    base_name: str | None
    attribute_name: str


@dataclass(frozen=True, slots=True)
class ReferenceFacts:
    """Imports and ordered import-or-attribute reference events."""

    imports: tuple[ImportFact, ...]
    events: tuple[ImportFact | AttributeReferenceFact, ...]


@dataclass(frozen=True, slots=True)
class CommentFact:
    """One source comment and its diagnostic display position."""

    path: Path
    line: int
    column: int
    text: str


@dataclass(frozen=True, slots=True)
class FunctionMetricFact:
    """Reusable structural metrics for one function."""

    location: SourceLocation
    name: str
    statement_count: int
    distinct_call_count: int
    assigned_local_count: int
    parameter_count: int
    positional_parameter_count: int
    dunder: bool


@dataclass(frozen=True, slots=True)
class FunctionFacts:
    """Functions in compatibility and top-level source order."""

    functions: tuple[FunctionMetricFact, ...]
    top_level: tuple[FunctionMetricFact, ...]


@dataclass(frozen=True, slots=True)
class ParameterMutationFact:
    """The first direct mutation of one function parameter."""

    function_name: str
    parameter_name: str
    location: SourceLocation
    returned: bool
    dunder: bool
    setter: bool


@dataclass(frozen=True, slots=True)
class MeaningfulReturnFact:
    """The first meaningful return owned by a function."""

    function_name: str
    location: SourceLocation


@dataclass(frozen=True, slots=True)
class HygieneFacts:
    """Backend-neutral locations for syntax-based hygiene policies."""

    multiline_docstrings: tuple[SourceLocation, ...]
    raw_builtin_raises: tuple[SourceLocation, ...]
    assertions: tuple[SourceLocation, ...]
    swallowed_exception_probes: tuple[SourceLocation, ...]
    unnamed_string_decisions: tuple[SourceLocation, ...]
    magic_numeric_comparisons: tuple[SourceLocation, ...]


@dataclass(frozen=True, slots=True)
class DataclassFact:
    """One dataclass declaration and its field/frozen metadata."""

    name: str
    location: SourceLocation
    field_names: frozenset[str]
    frozen: bool
    shape_candidate: bool


@dataclass(frozen=True, slots=True)
class ModuleStatementFact:
    """One top-level non-docstring statement relevant to module-role policy."""

    location: SourceLocation
    import_statement: bool
    model_class: bool
    exception_class: bool


@dataclass(frozen=True, slots=True)
class ModuleDeclarationFacts:
    """Top-level statements and classified declarations in one module."""

    statements: tuple[ModuleStatementFact, ...]
    model_locations: tuple[SourceLocation, ...]
    exception_locations: tuple[SourceLocation, ...]


@dataclass(frozen=True, slots=True)
class ParametrizeCaseFact:
    """One visible pytest parametrization case expression."""

    location: SourceLocation
    constructor_name: str | None
    dictionary: bool


@dataclass(frozen=True, slots=True)
class ParametrizeFact:
    """Structured pytest parametrization decorator metadata."""

    argument_count: int
    parameter_name: str | None
    ids_present: bool
    description_lambda_ids: bool
    values_is_name: bool
    values_is_list_comprehension: bool
    values_is_sequence: bool
    values_empty: bool
    cases: tuple[ParametrizeCaseFact, ...]


@dataclass(frozen=True, slots=True)
class PytestFunctionFact:
    """Reusable syntax metadata for one test function."""

    name: str
    location: SourceLocation
    parameter_names: frozenset[str]
    test_case_annotation_name: str | None
    parametrize: ParametrizeFact | None
    references_expected_field: bool
    conditional_locations: tuple[SourceLocation, ...]


@dataclass(frozen=True, slots=True)
class PytestModuleFacts:
    """Reusable module-shape metadata for test convention policy."""

    empty_or_docstring_only: bool
    scenario_invalid_locations: tuple[SourceLocation, ...]
    top_level_helper_locations: tuple[SourceLocation, ...]
    test_case_list_locations: tuple[SourceLocation, ...]
    private_after_test_locations: tuple[SourceLocation, ...]
