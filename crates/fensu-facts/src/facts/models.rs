//! Fact models shared across extraction entries.

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub struct LocatedNode {
    pub kind: &'static str,
    pub span: Option<(u32, u32, u32, u32)>,
}

#[derive(Clone, Debug, Eq, PartialEq)]
pub struct CommentRow {
    pub line: u32,
    pub column: u32,
    pub text: String,
}

#[derive(Clone, Debug, Eq, PartialEq)]
pub struct NamedLocationRow {
    pub name: String,
    pub line: u32,
    pub column: u32,
}

#[derive(Clone, Debug, Eq, PartialEq)]
pub struct LocalAnnotationRow {
    pub name: String,
    pub line: u32,
    pub column: u32,
    pub scalar_literal: bool,
}

#[derive(Clone, Debug, Default, Eq, PartialEq)]
pub struct AnnotationRows {
    pub parameters: Vec<NamedLocationRow>,
    pub returns: Vec<NamedLocationRow>,
    pub locals: Vec<LocalAnnotationRow>,
    pub module_variables: Vec<NamedLocationRow>,
    pub class_attributes: Vec<NamedLocationRow>,
}

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

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub struct TypeDeclarationRow {
    pub line: u32,
    pub column: u32,
    pub private: bool,
}

#[derive(Clone, Debug, Eq, PartialEq)]
pub struct NamedCallRow {
    pub line: u32,
    pub column: u32,
    pub name: Option<String>,
}

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

#[derive(Clone, Debug, Eq, PartialEq)]
pub struct ParameterMutationOccurrenceRow {
    pub function_name: String,
    pub parameter_name: String,
    pub parameter_kind: String,
    pub line: u32,
    pub column: u32,
    pub returned: bool,
    pub dunder: bool,
    pub setter: bool,
}

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub struct SourceRangeRow {
    pub start_line: u32,
    pub start_column: u32,
    pub start_offset: u32,
    pub end_line: u32,
    pub end_column: u32,
    pub end_offset: u32,
}

#[derive(Clone, Debug, Eq, PartialEq)]
pub struct ImportAliasRow {
    pub imported_name: String,
    pub bound_name: String,
}

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

#[derive(Clone, Debug, Default, Eq, PartialEq)]
pub struct ReferenceRows {
    pub imports: Vec<ImportRow>,
    pub events: Vec<ReferenceEventRow>,
}

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

/// One expression resolved to an absolute imported module symbol.
#[derive(Clone, Debug, Eq, Hash, PartialEq)]
pub struct StaticReferenceRow {
    pub module_name: String,
    pub symbol_name: String,
}

/// One pytest parametrization dimension and its provable RuleCase values.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct DimensionRow {
    pub line: u32,
    pub column: u32,
    pub parameter_names: Vec<String>,
    pub values_location: Option<(u32, u32)>,
    pub rule_case_locations: Vec<(u32, u32)>,
    pub unknown_rule_case_count: bool,
}

/// One statically recognized fensu.evaluate_rule call.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct EvaluateRuleCallRow {
    pub line: u32,
    pub column: u32,
    pub test_function_name: Option<String>,
    pub test_function_location: Option<(u32, u32)>,
    pub rule_expression: Option<Vec<String>>,
    pub rule_location: Option<(u32, u32)>,
    pub rule_reference: Option<StaticReferenceRow>,
    pub test_case_expression: Option<Vec<String>>,
    pub test_case_location: Option<(u32, u32)>,
    pub test_case_form: String,
    pub case_locations: Vec<(u32, u32)>,
    pub unknown_case_count: bool,
}

/// One visible pytest parametrization case expression.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct ParametrizeCaseRow {
    pub line: u32,
    pub column: u32,
    pub constructor_name: Option<String>,
    pub dictionary: bool,
}

/// Structured pytest parametrization decorator metadata.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct ParametrizeRow {
    pub argument_count: u32,
    pub parameter_name: Option<String>,
    pub ids_present: bool,
    pub description_lambda_ids: bool,
    pub values_is_comprehension: bool,
    pub values_is_sequence: bool,
    pub values_empty: bool,
    pub cases: Vec<ParametrizeCaseRow>,
}

/// Reusable syntax metadata for one test function.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct TestFunctionRow {
    pub name: String,
    pub line: u32,
    pub column: u32,
    pub parameter_names: Vec<String>,
    pub test_case_annotation_name: Option<String>,
    pub parametrize: Option<ParametrizeRow>,
    pub references_expected_field: bool,
    pub conditional_locations: Vec<(u32, u32)>,
    pub dimensions: Vec<DimensionRow>,
}

#[derive(Clone, Debug, Eq, PartialEq)]
pub struct DefinitionIdentityRow {
    pub name: String,
    pub line: u32,
    pub column: u32,
}

#[derive(Clone, Debug, Eq, PartialEq)]
pub struct QualifiedReferenceRow {
    pub kind: String,
    pub name: Option<String>,
    pub base_name: Option<String>,
    pub receiver_base_name: Option<String>,
    pub parts: Vec<String>,
}

#[derive(Clone, Debug, Eq, PartialEq)]
pub struct ClassMethodRow {
    pub name: String,
    pub decorator_names: Vec<String>,
    pub line: u32,
    pub column: u32,
    pub owning_class: DefinitionIdentityRow,
}

#[derive(Clone, Debug, Eq, PartialEq)]
pub struct ClassDeclarationRow {
    pub name: String,
    pub base_names: Vec<String>,
    pub decorator_names: Vec<String>,
    pub line: u32,
    pub column: u32,
    pub top_level: bool,
    pub methods: Vec<ClassMethodRow>,
}

#[derive(Clone, Debug, Eq, PartialEq)]
pub struct AssignmentReferenceRow {
    pub line: u32,
    pub column: u32,
    pub owning_class: Option<DefinitionIdentityRow>,
    pub owning_function: Option<DefinitionIdentityRow>,
    pub target_names: Vec<String>,
    pub value_reference: Option<QualifiedReferenceRow>,
}

#[derive(Clone, Debug, PartialEq)]
pub struct LiteralArgumentRow {
    pub position: usize,
    pub kind: String,
    pub value: crate::facts::types::LiteralValueRow,
}

#[derive(Clone, Debug, PartialEq)]
pub struct RuleNamedCallRow {
    pub line: u32,
    pub column: u32,
    pub name: Option<String>,
    pub reference: QualifiedReferenceRow,
    pub owning_class: Option<DefinitionIdentityRow>,
    pub owning_function: Option<DefinitionIdentityRow>,
    pub enclosing_classes: Vec<DefinitionIdentityRow>,
    pub enclosing_functions: Vec<DefinitionIdentityRow>,
    pub inside_loop: bool,
    pub literal_arguments: Vec<LiteralArgumentRow>,
    pub bare_expression: bool,
    pub super_call: bool,
}

#[derive(Clone, Debug, Eq, PartialEq)]
pub struct LocalCallEdgeRow {
    pub line: u32,
    pub column: u32,
    pub caller: DefinitionIdentityRow,
    pub caller_class: Option<DefinitionIdentityRow>,
    pub callee: QualifiedReferenceRow,
    pub inside_loop: bool,
}

#[derive(Clone, Debug, Eq, PartialEq)]
pub struct ComparisonRow {
    pub line: u32,
    pub column: u32,
    pub operand_references: Vec<Option<QualifiedReferenceRow>>,
}
