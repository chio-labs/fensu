//! Extract first direct parameter mutations per function.

use ruff_python_ast::ModModule;

use crate::facts::helpers::metrics::mutations::parameter_mutation_rows;
use crate::facts::models::ParameterMutationRow;
use crate::positions::models::LineIndex;

/// Return first-mutation metadata for each function parameter in index order.
pub fn extract_parameter_mutations(
    module: &ModModule,
    index: &LineIndex,
    source: &str,
) -> Vec<ParameterMutationRow> {
    parameter_mutation_rows(module, index, source)
}
