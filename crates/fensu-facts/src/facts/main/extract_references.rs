//! Extract grouped imports and breadth-first reference events.

use ruff_python_ast::ModModule;

use crate::facts::helpers::references::events::reference_rows;
use crate::facts::models::ReferenceRows;
use crate::positions::models::LineIndex;

/// Return import rows and ordered import-or-attribute events.
pub fn extract_references(module: &ModModule, index: &LineIndex, source: &str) -> ReferenceRows {
    reference_rows(module, index, source)
}
