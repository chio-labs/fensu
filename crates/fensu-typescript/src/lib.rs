//! Owned TypeScript and JavaScript parser facts.
#![forbid(unsafe_code)]

pub mod constants;
pub mod models;
pub mod parser;

pub use constants::{CACHE_CONTRACT_VERSION, PARSER_CONTRACT_VERSION};
pub use models::{
    ClassFact, FunctionFact, ImportBindingFact, ImportFact, JsonCallFact, LocalBindingFact,
    ModelFact, ModelKind, ModuleFacts, ParameterizedTestFact, ParseDiagnostic, SourceKind,
    SourceSpan, TopLevelBindingFact,
};
pub use parser::{
    parse, parse_binding_pattern, parse_expression, parse_formal_parameters, parse_javascript,
    parse_type_parameters, parse_typescript,
};
