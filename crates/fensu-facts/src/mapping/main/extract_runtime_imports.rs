//! Extract imports that bind names at module runtime.

use ruff_python_ast::ModModule;

use crate::mapping::_helpers::imports::mapping_imports;
use crate::mapping::models::MappingImportRow;

pub fn extract_runtime_imports(module: &ModModule) -> Vec<MappingImportRow> {
    mapping_imports(module).0
}
