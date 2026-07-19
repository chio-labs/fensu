//! Extract structural function metrics and top-level mapping.

use ruff_python_ast::ModModule;

use crate::facts::helpers::metrics::functions::function_metric_rows;
use crate::facts::models::FunctionMetricRow;
use crate::positions::models::LineIndex;

/// Return metric rows in index order plus top-level row indexes in body order.
pub fn extract_functions(
    module: &ModModule,
    index: &LineIndex,
    source: &str,
) -> (Vec<FunctionMetricRow>, Vec<usize>) {
    function_metric_rows(module, index, source)
}
