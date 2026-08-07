//! Register Fensu's private native extension.

use crate::cache::main::register_cache;
use crate::extension::_helpers::evaluation::{execution_planning, rule_bindings};
#[cfg(feature = "memory")]
use crate::extension::_helpers::memory::registration;
use pyo3::prelude::{pymodule, Bound, PyModule, PyModuleMethods, PyResult};
use pyo3::wrap_pyfunction;

/// Register Fensu's private native Python module.
#[pymodule]
pub fn _native(module: &Bound<'_, PyModule>) -> PyResult<()> {
    fensu_facts::extension::main::register_module::register_fact_functions(module)?;
    module.add_class::<rule_bindings::NativeExecutionBatch>()?;
    module.add_function(wrap_pyfunction!(
        rule_bindings::plan_native_execution_batch,
        module
    )?)?;
    module.add_function(wrap_pyfunction!(
        rule_bindings::evaluate_native_execution_batch,
        module
    )?)?;
    module.add_function(wrap_pyfunction!(
        rule_bindings::native_execution_programs,
        module
    )?)?;
    module.add_function(wrap_pyfunction!(
        rule_bindings::native_rule_fact_families,
        module
    )?)?;
    module.add_function(wrap_pyfunction!(
        rule_bindings::native_generated_policy_owners,
        module
    )?)?;
    module.add_function(wrap_pyfunction!(
        execution_planning::select_native_execution_files,
        module
    )?)?;
    module.add_function(wrap_pyfunction!(
        execution_planning::plan_native_execution_owners,
        module
    )?)?;
    module.add_function(wrap_pyfunction!(
        execution_planning::partition_native_execution_targets,
        module
    )?)?;
    register_cache::register_cache_functions(module)?;
    #[cfg(feature = "memory")]
    registration::register_memory_functions(module)?;
    Ok(())
}
