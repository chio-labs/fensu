//! Extract statically recognized public rule-harness calls.

use ruff_python_ast::ModModule;

use crate::facts::helpers::harness::calls::evaluate_rule_call_rows;
use crate::facts::models::EvaluateRuleCallRow;
use crate::positions::models::LineIndex;

/// Return every unshadowed strata.evaluate_rule call in index order.
pub fn extract_evaluate_rule_calls(
    module: &ModModule,
    index: &LineIndex,
    source: &str,
) -> Vec<EvaluateRuleCallRow> {
    evaluate_rule_call_rows(module, index, source)
}
