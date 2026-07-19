//! Extract complete native mapping facts.

use ruff_python_ast::ModModule;

use crate::facts::mapping::helpers::extraction::build_mapping_rows;
use crate::facts::mapping::models::MappingRows;
use crate::positions::models::LineIndex;

pub fn extract_mapping_facts(module: &ModModule, index: &LineIndex, source: &str) -> MappingRows {
    build_mapping_rows(module, index, source, false)
}
