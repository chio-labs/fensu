//! Return focused compiled metadata for one memory relation.

use crate::engine::helpers::reporting::schema_metadata;
use crate::engine::models::MemorySchemaRelation;

/// Return focused metadata for one `memory.*` relation name.
pub fn memory_relation_schema(name: &str) -> Option<MemorySchemaRelation> {
    schema_metadata::find_relation(name)
}
