//! Extract descriptive function-contract rows in source order.

use ruff_python_ast::{ModModule, PythonVersion};

use crate::facts::helpers::contracts::rows::function_contract_rows;
use crate::facts::models::FunctionContractRow;
use crate::positions::models::LineIndex;

/// Return descriptive contracts from one owned-body walk per function.
pub fn extract_function_contracts(
    module: &ModModule,
    index: &LineIndex,
    source: &str,
    version: PythonVersion,
) -> Vec<FunctionContractRow> {
    function_contract_rows(module, index, source, version)
}
