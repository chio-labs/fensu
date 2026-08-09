//! Owned Svelte structure and embedded TypeScript parser facts.
#![forbid(unsafe_code)]

pub mod constants;
pub mod models;
pub mod parser;

pub use constants::{CACHE_CONTRACT_VERSION, PARSER_CONTRACT_VERSION, RECOVERY_NODE_KINDS};
pub use models::{ParseDiagnostic, RuneFact, ScriptContext, ScriptFact, SvelteFacts};
pub use parser::parse;
