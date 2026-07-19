"""Backend-neutral source identity and location models."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from strata.analysis.types import RuleCaseForm


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
    scalar_literal: bool


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
class ProjectFunctionFact:
    """One top-level function and whether its annotation promises a result."""

    name: str
    meaningful_result: bool


@dataclass(frozen=True, slots=True)
class DiscardedProjectCallFact:
    """One discarded call that can be resolved within the project."""

    location: SourceLocation
    module_name: str | None
    function_name: str


@dataclass(frozen=True, slots=True)
class ProjectCallFacts:
    """Resolvable discarded calls for one module."""

    discarded_calls: tuple[DiscardedProjectCallFact, ...]


@dataclass(frozen=True, slots=True)
class ProjectDependency:
    """One requester-to-path dependency observed by a project query."""

    requester: Path
    query_path: Path
    dependency: Path
    kind: str
    answer: None | bool | str | tuple[Path, ...]
    pattern: str | None = None
    recursive: bool = False


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
class ParameterMutationOccurrenceFact:
    """One direct mutation occurrence of a function parameter."""

    function_name: str
    parameter_name: str
    parameter_kind: str
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
class FunctionContractFact:
    """Descriptive return and generator facts for one function."""

    function_name: str
    location: SourceLocation
    return_annotation_category: str
    return_annotation: str
    contains_yield: bool
    meaningful_return_location: SourceLocation | None


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
    assignment_statement: bool
    explicit_type_alias: bool
    type_checking_import_block: bool
    model_class: bool
    type_class: bool
    exception_class: bool
    assignment_target_names: tuple[str, ...]
    function_name: str | None
    class_name: str | None
    dataclass_class: bool
    docstring_statement: bool
    all_assignment: bool
    rule_decorated_function: bool
    nonexecuting_import_guard: bool


@dataclass(frozen=True, slots=True)
class TypeDeclarationFact:
    """One type-layer declaration and its policy-relevant visibility."""

    location: SourceLocation
    private: bool


@dataclass(frozen=True, slots=True)
class DefinitionIdentity:
    """The name and declaration location identifying a class or function."""

    name: str
    location: SourceLocation


@dataclass(frozen=True, slots=True)
class QualifiedReferenceFact:
    """Lenient and strict static identity for one reference expression."""

    kind: str
    name: str | None
    base_name: str | None
    receiver_base_name: str | None
    parts: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class ClassMethodFact:
    """One direct named method declared by a class."""

    name: str
    decorator_names: tuple[str, ...]
    location: SourceLocation
    owning_class: DefinitionIdentity


@dataclass(frozen=True, slots=True)
class ClassDeclarationFact:
    """One class declaration with direct method metadata."""

    name: str
    base_names: tuple[str, ...]
    decorator_names: tuple[str, ...]
    location: SourceLocation
    top_level: bool
    methods: tuple[ClassMethodFact, ...]


@dataclass(frozen=True, slots=True)
class AssignmentReferenceFact:
    """One assignment and any strict qualified reference on its right side."""

    location: SourceLocation
    owning_class: DefinitionIdentity | None
    owning_function: DefinitionIdentity | None
    target_names: tuple[str, ...]
    value_reference: QualifiedReferenceFact | None


@dataclass(frozen=True, slots=True)
class LiteralArgumentFact:
    """One literal positional call argument with its source position."""

    position: int
    kind: str
    value: str | bytes | int | float | complex | bool | None


@dataclass(frozen=True, slots=True)
class NamedCallFact:
    """One call with nearest-first lexical owner chains."""

    location: SourceLocation
    name: str | None
    reference: QualifiedReferenceFact | None = None
    owning_class: DefinitionIdentity | None = None
    owning_function: DefinitionIdentity | None = None
    enclosing_classes: tuple[DefinitionIdentity, ...] = ()
    enclosing_functions: tuple[DefinitionIdentity, ...] = ()
    inside_loop: bool = False
    literal_arguments: tuple[LiteralArgumentFact, ...] = ()
    bare_expression: bool = False
    super_call: bool = False


@dataclass(frozen=True, slots=True)
class LocalCallEdgeFact:
    """One call attributed to an enclosing named caller, nearest caller first."""

    location: SourceLocation
    caller: DefinitionIdentity
    caller_class: DefinitionIdentity | None
    callee: QualifiedReferenceFact
    inside_loop: bool


@dataclass(frozen=True, slots=True)
class ComparisonFact:
    """One comparison with references aligned to direct operand positions."""

    location: SourceLocation
    operand_references: tuple[QualifiedReferenceFact | None, ...]


@dataclass(frozen=True, slots=True)
class ModuleDeclarationFacts:
    """Top-level statements and classified declarations in one module."""

    statements: tuple[ModuleStatementFact, ...]
    empty_or_docstring_only: bool
    pure_reexport: bool
    top_level_class_count: int
    all_assignment_locations: tuple[SourceLocation, ...]
    import_time_call_locations: tuple[SourceLocation, ...]
    imported_main_entry_names: frozenset[str]
    main_calls: tuple[NamedCallFact, ...]
    model_locations: tuple[SourceLocation, ...]
    type_declarations: tuple[TypeDeclarationFact, ...]
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
    values_is_comprehension: bool
    values_is_sequence: bool
    values_empty: bool
    cases: tuple[ParametrizeCaseFact, ...]


@dataclass(frozen=True, slots=True)
class ParametrizeDimensionFact:
    """One pytest parametrization dimension and its provable RuleCase values."""

    location: SourceLocation
    parameter_names: tuple[str, ...]
    values_location: SourceLocation | None
    rule_case_locations: tuple[SourceLocation, ...]
    unknown_rule_case_count: bool

    @property
    def provable_rule_case_count(self) -> int:
        """Return the number of statically visible RuleCase values."""

        return len(self.rule_case_locations)


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
    parametrize_dimensions: tuple[ParametrizeDimensionFact, ...] = ()


@dataclass(frozen=True, slots=True)
class StaticReferenceFact:
    """One expression resolved to an absolute imported module symbol."""

    module_name: str
    symbol_name: str


@dataclass(frozen=True, slots=True)
class EvaluateRuleCallFact:
    """One statically recognized strata.evaluate_rule call."""

    location: SourceLocation
    test_function_name: str | None
    test_function_location: SourceLocation | None
    rule_expression: tuple[str, ...] | None
    rule_location: SourceLocation | None
    rule_reference: StaticReferenceFact | None
    test_case_expression: tuple[str, ...] | None
    test_case_location: SourceLocation | None
    test_case_form: RuleCaseForm
    case_locations: tuple[SourceLocation, ...]
    unknown_case_count: bool

    @property
    def provable_case_count(self) -> int:
        """Return the statically proven RuleCase cardinality for this call."""

        return len(self.case_locations)


@dataclass(frozen=True, slots=True)
class RuleTestAssociationFact:
    """Deduplicated static harness coverage for one test function and rule."""

    rule_reference: StaticReferenceFact
    test_function_name: str
    test_function_location: SourceLocation
    call_locations: tuple[SourceLocation, ...]
    case_locations: tuple[SourceLocation, ...]
    unknown_case_count: bool

    @property
    def provable_case_count(self) -> int:
        """Return the deduplicated statically proven case count."""

        return len(self.case_locations)


@dataclass(frozen=True, slots=True)
class PytestModuleFacts:
    """Reusable module-shape metadata for test convention policy."""

    empty_or_docstring_only: bool
    scenario_invalid_locations: tuple[SourceLocation, ...]
    top_level_helper_locations: tuple[SourceLocation, ...]
    test_case_list_locations: tuple[SourceLocation, ...]
    private_after_test_locations: tuple[SourceLocation, ...]
