//! Owned semantic models exposed by the TypeScript parser.

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum SourceKind {
    JavaScript,
    JavaScriptModule,
    JavaScriptCommonJs,
    JavaScriptJsx,
    TypeScript,
    TypeScriptModule,
    TypeScriptCommonJs,
    TypeScriptDefinition,
    TypeScriptModuleDefinition,
    TypeScriptCommonJsDefinition,
    TypeScriptJsx,
}

#[derive(Clone, Debug, Eq, PartialEq)]
pub struct SourceSpan {
    pub start: usize,
    pub end: usize,
    pub line: usize,
    pub column: usize,
}

#[derive(Clone, Debug, Eq, PartialEq)]
pub struct ParseDiagnostic {
    pub message: String,
    pub span: SourceSpan,
}

#[derive(Clone, Debug, Eq, PartialEq)]
pub struct ImportFact {
    pub specifier: String,
    pub binding_count: usize,
    pub type_only: bool,
    pub namespace: bool,
    pub bindings: Vec<ImportBindingFact>,
    pub span: SourceSpan,
}

#[derive(Clone, Debug, Eq, PartialEq)]
pub struct ImportBindingFact {
    pub local_name: String,
    pub imported_name: String,
}

#[derive(Clone, Debug, Eq, PartialEq)]
pub struct ClassFact {
    pub name: String,
    pub exported: bool,
    pub error_class: bool,
    pub span: SourceSpan,
}

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum ModelKind {
    Interface,
    TypeLiteralAlias,
}

#[derive(Clone, Debug, Eq, PartialEq)]
pub struct ModelFact {
    pub name: String,
    pub kind: ModelKind,
    pub exported: bool,
    pub readonly_shape: bool,
    pub property_names: Vec<String>,
    pub span: SourceSpan,
}

#[derive(Clone, Debug, Eq, PartialEq)]
pub struct ParameterizedTestFact {
    pub span: SourceSpan,
    pub typed: bool,
    pub local_case_type: bool,
    pub case_type_name: Option<String>,
    pub local_readonly_case_type: bool,
    pub has_description: bool,
    pub has_expected: bool,
    pub inline_cases: bool,
    pub nonempty_cases: bool,
    pub object_cases: bool,
    pub title_uses_description: bool,
    pub callback_name: Option<String>,
    pub has_expectation: bool,
    pub uses_expected: bool,
    pub has_branch: bool,
    pub mutates_case: bool,
}

#[derive(Clone, Debug, Eq, PartialEq)]
pub struct FunctionFact {
    pub name: String,
    pub qualified_name: String,
    pub exported: bool,
    pub export_owner: Option<String>,
    pub parameter_count: usize,
    pub parameters_annotated: bool,
    pub return_type: Option<String>,
    pub statement_count: usize,
    pub distinct_call_count: usize,
    pub local_count: usize,
    pub span: SourceSpan,
}

#[derive(Clone, Debug, Eq, PartialEq)]
pub struct JsonCallFact {
    pub asserted: bool,
    pub schema_decoded: bool,
    pub span: SourceSpan,
}

#[derive(Clone, Debug, Eq, PartialEq)]
pub struct TestCallFact {
    pub name: String,
    pub span: SourceSpan,
}

#[derive(Clone, Debug, Eq, PartialEq)]
pub struct LocalBindingFact {
    pub name: String,
    pub function_name: String,
    pub scalar_literal: bool,
    pub explicitly_typed: bool,
    pub satisfies_type: bool,
    pub generic_call_or_new: bool,
    pub span: SourceSpan,
}

#[derive(Clone, Debug, Eq, PartialEq)]
pub struct TopLevelBindingFact {
    pub name: String,
    pub initializer_call: Option<String>,
    pub initializer_call_span: Option<SourceSpan>,
    pub span: SourceSpan,
}

#[derive(Clone, Debug, Eq, PartialEq)]
pub struct CallFact {
    pub name: String,
    pub function_name: Option<String>,
    pub cleanup_target: Option<String>,
    pub ancestor_calls: Vec<String>,
    pub function_argument: bool,
    pub returned_cleanup: bool,
    pub span: SourceSpan,
}

#[derive(Clone, Debug, Eq, PartialEq)]
pub struct StringFact {
    pub value: String,
    pub static_segments: Vec<String>,
    pub complete: bool,
    pub span: SourceSpan,
}

#[derive(Clone, Debug, Eq, PartialEq)]
pub struct MutationFact {
    pub root_name: String,
    pub span: SourceSpan,
}

#[derive(Clone, Debug, Eq, PartialEq)]
pub struct ReturnObjectFact {
    pub function_name: Option<String>,
    pub member_count: usize,
    pub member_names: Vec<String>,
    pub span: SourceSpan,
}

#[derive(Clone, Debug, Eq, PartialEq)]
pub struct ResourceFact {
    pub family: String,
    pub binding_name: Option<String>,
    pub ancestor_calls: Vec<String>,
    pub span: SourceSpan,
}

impl LocalBindingFact {
    #[must_use]
    pub const fn requires_explicit_type(&self) -> bool {
        !self.scalar_literal
            && !self.explicitly_typed
            && !self.satisfies_type
            && !self.generic_call_or_new
    }
}

#[derive(Clone, Debug, Default, Eq, PartialEq)]
pub struct ModuleFacts {
    pub imports: Vec<ImportFact>,
    pub imported_binding_count: usize,
    pub classes: Vec<ClassFact>,
    pub models: Vec<ModelFact>,
    pub functions: Vec<FunctionFact>,
    pub local_bindings: Vec<LocalBindingFact>,
    pub top_level_bindings: Vec<TopLevelBindingFact>,
    pub top_level_calls: Vec<TopLevelBindingFact>,
    pub re_exports: Vec<SourceSpan>,
    pub public_export_count: usize,
    pub runtime_declaration_count: usize,
    pub top_level_function_count: usize,
    pub parameterized_tests: Vec<ParameterizedTestFact>,
    pub test_calls: Vec<TestCallFact>,
    pub json_calls: Vec<JsonCallFact>,
    pub public_any: Vec<SourceSpan>,
    pub calls: Vec<CallFact>,
    pub strings: Vec<StringFact>,
    pub imported_mutations: Vec<MutationFact>,
    pub return_objects: Vec<ReturnObjectFact>,
    pub resources: Vec<ResourceFact>,
    pub cleanup_returns: Vec<SourceSpan>,
}
