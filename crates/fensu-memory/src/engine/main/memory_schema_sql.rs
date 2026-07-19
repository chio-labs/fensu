//! Expose the versioned SQLite memory schema and convenience views.

use crate::engine::constants;

/// Return the complete deterministic SQL contract for a memory index.
pub fn memory_schema_sql() -> &'static str {
    constants::MEMORY_SCHEMA_SQL
}
