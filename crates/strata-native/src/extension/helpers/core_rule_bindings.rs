//! Python bindings for batched native core-rule evaluation.

use pyo3::{pyfunction, Py, Python};
use rayon::iter::{IntoParallelRefIterator, ParallelIterator};
use std::collections::HashMap;
use strata_facts::extension::models::ProgramHandle;

use crate::rules::constants::NATIVE_RULE_FACT_FAMILIES;
use crate::rules::main::evaluate_core_rules::evaluate_core_rules;
use crate::rules::models::NativeFaultRow;
use crate::rules::models::NativeRuleContext;

type NativeFaultTuple = (String, u32, u32, Option<String>);
type NativeRuleRequestTuple = (
    Py<ProgramHandle>,
    Vec<String>,
    String,
    Option<String>,
    bool,
    HashMap<String, u32>,
);

#[pyfunction]
pub(crate) fn evaluate_native_core_rules(
    py: Python<'_>,
    requests: Vec<NativeRuleRequestTuple>,
) -> Vec<Vec<NativeFaultTuple>> {
    py.detach(move || {
        requests
            .par_iter()
            .map(|(handle, codes, scope, role, is_main_module, thresholds)| {
                let context = NativeRuleContext {
                    scope: scope.clone(),
                    role: role.clone(),
                    is_main_module: *is_main_module,
                    thresholds: thresholds.clone(),
                };
                evaluate_core_rules(handle.get(), codes, &context)
                    .into_iter()
                    .map(as_tuple)
                    .collect()
            })
            .collect()
    })
}

#[pyfunction]
pub(crate) fn native_rule_fact_families() -> Vec<(String, Vec<String>)> {
    NATIVE_RULE_FACT_FAMILIES
        .iter()
        .map(|(code, families)| {
            (
                (*code).to_owned(),
                families.iter().map(|family| (*family).to_owned()).collect(),
            )
        })
        .collect()
}

fn as_tuple(row: NativeFaultRow) -> NativeFaultTuple {
    (row.code, row.line, row.column, row.message)
}
