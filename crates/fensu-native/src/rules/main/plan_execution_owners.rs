//! Expose shared native rule applicability and execution-owner planning.

use crate::rules::_helpers::execution_planning::build_execution_plan;
use crate::rules::models::{NativeExecutionPlan, NativeExecutionRule, NativeExecutionTarget};

pub fn plan_execution_owners(
    targets: &[NativeExecutionTarget],
    rules: &[NativeExecutionRule],
) -> Result<Vec<NativeExecutionPlan>, String> {
    build_execution_plan(targets, rules)
}
