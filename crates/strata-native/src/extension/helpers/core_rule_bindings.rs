//! Python bindings for batched native core-rule evaluation.

use pyo3::exceptions::PyValueError;
use pyo3::{pyfunction, Py, PyResult, Python};
use rayon::iter::{IntoParallelRefIterator, ParallelIterator};
use std::collections::HashMap;
use strata_facts::extension::models::ProgramHandle;

use crate::rules::constants::NATIVE_RULE_FACT_FAMILIES;
use crate::rules::main::evaluate_core_rules::evaluate_core_rules;
use crate::rules::main::plan_core_rule_queries::plan_core_rule_queries;
use crate::rules::models::{NativeFaultRow, NativeRuleContext};

type NativeFaultTuple = (
    String,
    Option<String>,
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
    NativeProjectContextTuple,
);
type NativeProjectContextTuple = (
    Vec<String>,
    Vec<(String, String)>,
    HashMap<String, Vec<String>>,
    Vec<(String, String, String, String, u32, u32)>,
);

type NativeProjectQueryTuple = (String, String, String, String);

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
                    project_context,
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
                        tooling_packages: project_context.0.clone(),
                        scope_roots: project_context.1.clone(),
                        observations: project_context.2.clone(),
                        custom_registrations: project_context.3.clone(),
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
pub(crate) fn plan_native_core_rule_queries(
    py: Python<'_>,
    requests: Vec<NativeRuleRequestTuple>,
) -> Vec<Vec<NativeProjectQueryTuple>> {
    py.detach(move || {
        requests
            .par_iter()
            .map(|request| {
                let context = context_from_request(request);
                plan_core_rule_queries(request.0.get(), &request.1, &context)
                    .into_iter()
                    .map(|query| (query.key(), query.kind, query.path, query.argument))
                    .collect()
            })
            .collect()
    })
}

fn context_from_request(request: &NativeRuleRequestTuple) -> NativeRuleContext {
    NativeRuleContext {
        scope: request.2.clone(),
        role: request.3.clone(),
        is_main_module: request.4,
        thresholds: request.5.clone(),
        repository_path: request.6.clone(),
        contracts: request.7.clone(),
        relative_parts: request.8.clone(),
        is_entry_module: request.9,
        package_name: request.10.clone(),
        tooling_packages: request.11 .0.clone(),
        scope_roots: request.11 .1.clone(),
        observations: request.11 .2.clone(),
        custom_registrations: request.11 .3.clone(),
    }
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
        row.path,
        location.map(|(line, _)| line),
        location.map(|(_, column)| column),
        row.message,
        row.remediation,
    )
}
