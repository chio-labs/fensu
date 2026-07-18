//! Python bindings for batched native core-rule evaluation.

use pyo3::{pyfunction, Py, Python};
use rayon::iter::{IntoParallelRefIterator, ParallelIterator};
use strata_facts::extension::models::ProgramHandle;

use crate::rules::constants::NATIVE_RULE_FACT_FAMILIES;
use crate::rules::main::evaluate_core_rules::evaluate_core_rules;
use crate::rules::models::NativeFaultRow;

type NativeFaultTuple = (String, u32, u32, String);

#[pyfunction]
pub(crate) fn evaluate_native_core_rules(
    py: Python<'_>,
    requests: Vec<(Py<ProgramHandle>, Vec<String>)>,
) -> Vec<Vec<NativeFaultTuple>> {
    py.detach(move || {
        requests
            .par_iter()
            .map(|(handle, codes)| {
                evaluate_core_rules(handle.get(), codes)
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
    (row.code.to_owned(), row.line, row.column, row.message)
}
