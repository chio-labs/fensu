//! Fact models shared across extraction entries.

/// One traversed node: its CPython kind name and optional CPython span.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub struct LocatedNode {
    pub kind: &'static str,
    pub span: Option<(u32, u32, u32, u32)>,
}

/// One source comment with tokenize-convention line and character column.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct CommentRow {
    pub line: u32,
    pub column: u32,
    pub text: String,
}

/// One named fact location using CPython line and byte-column conventions.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct NamedLocationRow {
    pub name: String,
    pub line: u32,
    pub column: u32,
}

/// One first local binding missing an annotation.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct LocalAnnotationRow {
    pub name: String,
    pub line: u32,
    pub column: u32,
    pub scalar_literal: bool,
}

/// Missing-annotation rows collected by one shared traversal.
#[derive(Clone, Debug, Default, Eq, PartialEq)]
pub struct AnnotationRows {
    pub parameters: Vec<NamedLocationRow>,
    pub returns: Vec<NamedLocationRow>,
    pub locals: Vec<LocalAnnotationRow>,
    pub module_variables: Vec<NamedLocationRow>,
    pub class_attributes: Vec<NamedLocationRow>,
}

/// One top-level module statement classified for module-role policy.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct ModuleStatementRow {
    pub line: u32,
    pub column: u32,
    pub import_statement: bool,
    pub assignment_statement: bool,
    pub explicit_type_alias: bool,
    pub type_checking_import_block: bool,
    pub model_class: bool,
    pub type_class: bool,
    pub exception_class: bool,
    pub assignment_target_names: Vec<String>,
    pub function_name: Option<String>,
    pub class_name: Option<String>,
    pub dataclass_class: bool,
    pub docstring_statement: bool,
    pub all_assignment: bool,
    pub rule_decorated_function: bool,
    pub nonexecuting_import_guard: bool,
}

/// One type-layer declaration with its policy-relevant visibility.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub struct TypeDeclarationRow {
    pub line: u32,
    pub column: u32,
    pub private: bool,
}

/// One call with a statically knowable bare name when available.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct NamedCallRow {
    pub line: u32,
    pub column: u32,
    pub name: Option<String>,
}

/// Classified module statements and declarations for one module.
#[derive(Clone, Debug, Default, Eq, PartialEq)]
pub struct ModuleDeclarationRows {
    pub statements: Vec<ModuleStatementRow>,
    pub empty_or_docstring_only: bool,
    pub pure_reexport: bool,
    pub top_level_class_count: u32,
    pub all_assignment_locations: Vec<(u32, u32)>,
    pub import_time_call_locations: Vec<(u32, u32)>,
    pub imported_main_entry_names: Vec<String>,
    pub main_calls: Vec<NamedCallRow>,
    pub model_locations: Vec<(u32, u32)>,
    pub type_declarations: Vec<TypeDeclarationRow>,
    pub exception_locations: Vec<(u32, u32)>,
}

/// Descriptive return and generator facts for one function.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct FunctionContractRow {
    pub function_name: String,
    pub line: u32,
    pub column: u32,
    pub category: String,
    pub annotation: Option<String>,
    pub contains_yield: bool,
    pub meaningful_return: Option<(u32, u32)>,
}

/// Reusable structural metrics for one function.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct FunctionMetricRow {
    pub line: u32,
    pub column: u32,
    pub name: String,
    pub statement_count: u32,
    pub distinct_call_count: u32,
    pub assigned_local_count: u32,
    pub parameter_count: u32,
    pub positional_parameter_count: u32,
    pub dunder: bool,
}

/// The first direct mutation of one function parameter.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct ParameterMutationRow {
    pub function_name: String,
    pub parameter_name: String,
    pub line: u32,
    pub column: u32,
    pub returned: bool,
    pub dunder: bool,
    pub setter: bool,
}

/// One end-exclusive source range with byte offsets.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub struct SourceRangeRow {
    pub start_line: u32,
    pub start_column: u32,
    pub start_offset: u32,
    pub end_line: u32,
    pub end_column: u32,
    pub end_offset: u32,
}

/// One imported name and its local binding.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct ImportAliasRow {
    pub imported_name: String,
    pub bound_name: String,
}

/// One import statement and its imported names.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct ImportRow {
    pub line: u32,
    pub column: u32,
    pub module_parts: Vec<String>,
    pub aliases: Vec<ImportAliasRow>,
    pub relative_level: u32,
    pub from_import: bool,
    pub top_level: bool,
}

/// One reference event: an import row index or an attribute reference.
#[derive(Clone, Debug, Eq, PartialEq)]
pub enum ReferenceEventRow {
    Import(usize),
    Attribute {
        line: u32,
        column: u32,
        base_name: Option<String>,
        attribute_name: String,
    },
}

/// Grouped imports and ordered reference events.
#[derive(Clone, Debug, Default, Eq, PartialEq)]
pub struct ReferenceRows {
    pub imports: Vec<ImportRow>,
    pub events: Vec<ReferenceEventRow>,
}

/// Reusable module-shape metadata for test convention policy.
#[derive(Clone, Debug, Default, Eq, PartialEq)]
pub struct TestModuleRows {
    pub empty_or_docstring_only: bool,
    pub scenario_invalid: Vec<(u32, u32)>,
    pub top_level_helpers: Vec<(u32, u32)>,
    pub test_case_lists: Vec<(u32, u32)>,
    pub private_after_test: Vec<(u32, u32)>,
}

/// Backend-neutral locations for syntax-based hygiene policies.
#[derive(Clone, Debug, Default, Eq, PartialEq)]
pub struct HygieneRows {
    pub multiline_docstrings: Vec<(u32, u32)>,
    pub raw_builtin_raises: Vec<(u32, u32)>,
    pub assertions: Vec<(u32, u32)>,
    pub swallowed_exception_probes: Vec<(u32, u32)>,
    pub unnamed_string_decisions: Vec<(u32, u32)>,
    pub magic_numeric_comparisons: Vec<(u32, u32)>,
}

/// Conditional and comprehension control-flow rows for one module.
#[derive(Clone, Debug, Default, Eq, PartialEq)]
pub struct ControlFlowRows {
    pub function_conditionals: Vec<FunctionConditionalRow>,
    pub complex_comprehensions: Vec<(u32, u32)>,
    pub top_level_test_conditionals: Vec<(u32, u32)>,
}

/// Conditional control flow owned by one function.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct FunctionConditionalRow {
    pub function_name: String,
    pub decorator_names: Vec<String>,
    pub range: SourceRangeRow,
}

/// One top-level dataclass declaration and its field metadata.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct DataclassRow {
    pub name: String,
    pub line: u32,
    pub column: u32,
    pub field_names: Vec<String>,
    pub frozen: bool,
    pub shape_candidate: bool,
}

/// One top-level function and whether its annotation promises a result.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct ProjectFunctionRow {
    pub name: String,
    pub meaningful_result: bool,
}

/// One discarded call that can be resolved within the project.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct DiscardedCallRow {
    pub line: u32,
    pub column: u32,
    pub module_name: Option<String>,
    pub function_name: String,
}
