//! Plan project observations for one native rule request.

use strata_facts::extension::models::ProgramHandle;

use crate::rules::helpers::project_queries::plan_project_queries;
use crate::rules::models::{NativeProjectQuery, NativeRuleContext};

pub fn plan_core_rule_queries(
    program: &ProgramHandle,
    codes: &[String],
    context: &NativeRuleContext,
) -> Vec<NativeProjectQuery> {
    plan_project_queries(program, codes, context)
}
