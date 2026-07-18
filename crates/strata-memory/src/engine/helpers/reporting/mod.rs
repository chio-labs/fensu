//! Summary, synchronization, and schema-reporting phases.

#[cfg(feature = "sqlite-engine")]
pub(crate) mod diagnostics;
#[cfg(feature = "sqlite-engine")]
pub(crate) mod schema_core;
#[cfg(feature = "sqlite-engine")]
pub(crate) mod schema_markdown;
#[cfg(feature = "sqlite-engine")]
pub(crate) mod schema_metadata;
#[cfg(feature = "sqlite-engine")]
pub(crate) mod schema_skill_view;
#[cfg(feature = "sqlite-engine")]
pub(crate) mod schema_views;
pub(crate) mod summaries;
#[cfg(feature = "sqlite-engine")]
pub(crate) mod synchronization;
