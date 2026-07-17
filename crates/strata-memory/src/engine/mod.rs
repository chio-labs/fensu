//! Memory indexing and retrieval engine.

#[cfg(feature = "duckdb-engine")]
pub(crate) mod constants;
#[cfg(feature = "duckdb-engine")]
pub mod errors;
mod helpers;
pub mod main;
pub mod models;
