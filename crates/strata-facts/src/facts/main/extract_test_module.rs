//! Extract reusable test module-shape metadata.

use ruff_python_ast::ModModule;

use crate::facts::helpers::references::test_shape::test_module_rows;
use crate::facts::models::TestModuleRows;
use crate::positions::models::LineIndex;

/// Return module-shape rows for test convention policy.
pub fn extract_test_module(module: &ModModule, index: &LineIndex, source: &str) -> TestModuleRows {
    test_module_rows(module, index, source)
}
