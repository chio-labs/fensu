//! Python bindings for batched native core-rule evaluation.

use pyo3::exceptions::PyValueError;
use pyo3::{pyfunction, Py, PyResult, Python};
use rayon::iter::{IntoParallelRefIterator, ParallelIterator};
use std::collections::HashMap;
use strata_facts::extension::models::ProgramHandle;

use crate::rules::constants::NATIVE_RULE_FACT_FAMILIES;
use crate::rules::main::evaluate_core_rules::evaluate_core_rules;
use crate::rules::models::NativeFaultRow;
use crate::rules::models::NativeRuleContext;

type NativeFaultTuple = (
    String,
    Option<u32>,
    Option<u32>,
    Option<String>,
    Option<String>,
);
type NativeRuleRequestTuple = (
    Py<ProgramHandle>,
    Vec<String>,
    String,
    Option<String>,
    bool,
    HashMap<String, u32>,
    String,
    Vec<(String, String)>,
    Vec<String>,
    bool,
    String,
    Vec<String>,
);

#[pyfunction]
pub(crate) fn evaluate_native_core_rules(
    py: Python<'_>,
    requests: Vec<NativeRuleRequestTuple>,
) -> PyResult<Vec<Vec<NativeFaultTuple>>> {
    py.detach(move || {
        let batches: Result<Vec<Vec<NativeFaultTuple>>, String> = requests
            .par_iter()
            .map(
                |(
                    handle,
                    codes,
                    scope,
                    role,
                    is_main_module,
                    thresholds,
                    repository_path,
                    contracts,
                    relative_parts,
                    is_entry_module,
                    package_name,
                    tooling_packages,
                )| {
                    let context = NativeRuleContext {
                        scope: scope.clone(),
                        role: role.clone(),
                        is_main_module: *is_main_module,
                        thresholds: thresholds.clone(),
                        repository_path: repository_path.clone(),
                        contracts: contracts.clone(),
                        relative_parts: relative_parts.clone(),
                        is_entry_module: *is_entry_module,
                        package_name: package_name.clone(),
                        tooling_packages: tooling_packages.clone(),
                    };
                    evaluate_core_rules(handle.get(), codes, &context)
                        .map(|rows| rows.into_iter().map(as_tuple).collect())
                },
            )
            .collect();
        batches.map_err(PyValueError::new_err)
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
    let location = (row.line != 0).then_some((row.line, row.column));
    (
        row.code,
        location.map(|(line, _)| line),
        location.map(|(_, column)| column),
        row.message,
        row.remediation,
    )
}
