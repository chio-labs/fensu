//! Expose compiled query-schema metadata without opening a repository database.

use crate::engine::helpers::reporting::schema_metadata;
use crate::engine::models::MemorySchemaOverview;

/// Return installed versions and all public memory relation summaries.
pub fn memory_schema() -> MemorySchemaOverview {
    schema_metadata::overview()
}
