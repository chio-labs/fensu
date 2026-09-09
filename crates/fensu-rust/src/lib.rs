//! Owned Rust workspace analysis engine.
#![forbid(unsafe_code)]

pub mod constants;
pub mod engine;
pub mod models;

pub use constants::{CACHE_CONTRACT_VERSION, METADATA_SETUP_CODE, PARSER_CONTRACT_VERSION};
pub use engine::analyze_repository;
pub use models::{AnalysisDiagnostic, RepositoryAnalysis};
