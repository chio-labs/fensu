//! Summary, synchronization, and schema-reporting phases.

#[cfg(feature = "duckdb-engine")]
pub(crate) mod diagnostics;
#[cfg(feature = "duckdb-engine")]
pub(crate) mod schema_core;
#[cfg(feature = "duckdb-engine")]
pub(crate) mod schema_markdown;
#[cfg(feature = "duckdb-engine")]
pub(crate) mod schema_metadata;
#[cfg(feature = "duckdb-engine")]
pub(crate) mod schema_skill_view;
#[cfg(feature = "duckdb-engine")]
pub(crate) mod schema_views;
pub(crate) mod summaries;
#[cfg(feature = "duckdb-engine")]
pub(crate) mod synchronization;
