//! Owned semantic models exposed by the Svelte parser.

use fensu_typescript::{ModuleFacts, SourceSpan};

#[derive(Clone, Debug, Eq, PartialEq)]
pub struct ParseDiagnostic {
    pub message: String,
    pub span: SourceSpan,
}

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum ScriptContext {
    Module,
    Instance,
}

#[derive(Clone, Debug, Eq, PartialEq)]
pub struct ScriptFact {
    pub context: ScriptContext,
    pub content_span: SourceSpan,
    pub facts: ModuleFacts,
}

#[derive(Clone, Debug, Eq, PartialEq)]
pub struct RuneFact {
    pub name: String,
    pub span: SourceSpan,
}

#[derive(Clone, Debug, Default, Eq, PartialEq)]
pub struct SvelteFacts {
    pub scripts: Vec<ScriptFact>,
    pub module_runes: Vec<RuneFact>,
}
