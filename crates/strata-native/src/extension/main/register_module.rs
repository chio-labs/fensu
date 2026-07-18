//! Register Strata's private native extension.

#[cfg(feature = "memory")]
use crate::extension::helpers::memory_registration;
use pyo3::prelude::{pymodule, Bound, PyModule, PyResult};

/// Register Strata's private native Python module.
#[pymodule]
pub fn _native(module: &Bound<'_, PyModule>) -> PyResult<()> {
    strata_facts::extension::main::register_module::register_fact_functions(module)?;
    #[cfg(feature = "memory")]
    memory_registration::register_memory_functions(module)?;
    Ok(())
}
