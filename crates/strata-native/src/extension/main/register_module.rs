//! Register Strata's private native extension.

use crate::extension::helpers::core_rule_bindings;
#[cfg(feature = "memory")]
use crate::extension::helpers::memory_registration;
use pyo3::prelude::{pymodule, Bound, PyModule, PyResult};
use pyo3::types::PyModuleMethods;
use pyo3::wrap_pyfunction;

/// Register Strata's private native Python module.
#[pymodule]
pub fn _native(module: &Bound<'_, PyModule>) -> PyResult<()> {
    strata_facts::extension::main::register_module::register_fact_functions(module)?;
    module.add_function(wrap_pyfunction!(
        core_rule_bindings::evaluate_native_core_rules,
        module
    )?)?;
    module.add_function(wrap_pyfunction!(
        core_rule_bindings::plan_native_core_rule_queries,
        module
    )?)?;
    module.add_function(wrap_pyfunction!(
        core_rule_bindings::native_rule_fact_families,
        module
    )?)?;
    #[cfg(feature = "memory")]
    memory_registration::register_memory_functions(module)?;
    Ok(())
}
