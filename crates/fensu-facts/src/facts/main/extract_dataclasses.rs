//! Extract top-level dataclass declarations and field metadata.

use ruff_python_ast::ModModule;

use crate::facts::helpers::declarations::rows::dataclass_rows;
use crate::facts::models::DataclassRow;
use crate::positions::models::LineIndex;

/// Return top-level dataclass rows in body order.
pub fn extract_dataclasses(
    module: &ModModule,
    index: &LineIndex,
    source: &str,
) -> Vec<DataclassRow> {
    dataclass_rows(module, index, source)
}
