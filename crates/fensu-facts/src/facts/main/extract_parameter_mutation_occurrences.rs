//! Extract every direct parameter mutation occurrence.

use ruff_python_ast::ModModule;

use crate::facts::helpers::rule_authoring::mutations::parameter_mutation_occurrence_rows;
use crate::facts::models::ParameterMutationOccurrenceRow;
use crate::positions::models::LineIndex;

/// Return complete parameter-mutation metadata in function and occurrence order.
pub fn extract_parameter_mutation_occurrences(
    module: &ModModule,
    index: &LineIndex,
    source: &str,
) -> Vec<ParameterMutationOccurrenceRow> {
    parameter_mutation_occurrence_rows(module, index, source)
}
