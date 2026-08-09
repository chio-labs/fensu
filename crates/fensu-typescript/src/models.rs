//! Owned semantic models exposed by the TypeScript parser.

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum SourceKind {
    JavaScript,
    JavaScriptJsx,
    TypeScript,
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
    pub span: SourceSpan,
}

#[derive(Clone, Debug, Eq, PartialEq)]
pub struct ClassFact {
    pub name: String,
    pub exported: bool,
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
    pub span: SourceSpan,
}

#[derive(Clone, Debug, Eq, PartialEq)]
pub struct FunctionFact {
    pub name: String,
    pub exported: bool,
    pub parameter_count: usize,
    pub parameters_annotated: bool,
    pub return_type: Option<String>,
    pub statement_count: usize,
    pub distinct_call_count: usize,
    pub local_count: usize,
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
}
