//! Internal memory engine phases grouped by responsibility.

#[cfg(feature = "duckdb-engine")]
pub(crate) mod publication;
#[cfg(feature = "duckdb-engine")]
pub(crate) mod querying;
pub(crate) mod reporting;
