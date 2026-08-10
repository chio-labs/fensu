//! Return native check results before aggregate report rendering.

use std::collections::HashSet;

use crate::check::models::StructuredCheckExecution;

pub(crate) fn execute_structured_check(
    arguments: &[String],
    target_names: &HashSet<String>,
) -> Result<StructuredCheckExecution, String> {
    crate::check::_helpers::execution::structured_checks(arguments, target_names)
}
