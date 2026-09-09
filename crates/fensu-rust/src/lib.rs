//! Owned Rust workspace analysis engine.
#![forbid(unsafe_code)]

pub mod configuration;
pub mod constants;
pub mod engine;
pub mod models;
pub mod rules;
pub mod types;

pub use constants::{CACHE_CONTRACT_VERSION, METADATA_SETUP_CODE, PARSER_CONTRACT_VERSION};
pub use models::{AnalysisDiagnostic, RepositoryAnalysis};
