//! Extract syntax-based hygiene locations.

use ruff_python_ast::ModModule;

use crate::facts::helpers::hygiene::checks::hygiene_rows;
use crate::facts::models::HygieneRows;
use crate::positions::models::LineIndex;

/// Return hygiene locations grouped by policy.
pub fn extract_hygiene(module: &ModModule, index: &LineIndex, source: &str) -> HygieneRows {
    hygiene_rows(module, index, source)
}
