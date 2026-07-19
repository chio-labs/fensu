//! Extract reusable syntax metadata for test functions.

use ruff_python_ast::ModModule;

use crate::facts::helpers::harness::functions::test_function_rows;
use crate::facts::models::TestFunctionRow;
use crate::positions::models::LineIndex;

/// Return test-function rows with parametrize metadata and dimensions.
pub fn extract_test_functions(
    module: &ModModule,
    index: &LineIndex,
    source: &str,
) -> Vec<TestFunctionRow> {
    test_function_rows(module, index, source)
}
