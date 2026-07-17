//! Register memory functions on the private native extension.

use pyo3::types::{PyModule, PyModuleMethods};
use pyo3::wrap_pyfunction;
use pyo3::{Bound, PyResult};

use crate::extension::helpers::memory_bindings;

pub(crate) fn register_memory_functions(module: &Bound<'_, PyModule>) -> PyResult<()> {
    module.add_function(wrap_pyfunction!(
        memory_bindings::memory_dependency_probe,
        module
    )?)?;
    module.add_function(wrap_pyfunction!(memory_bindings::memory_summary, module)?)?;
    module.add_function(wrap_pyfunction!(memory_bindings::memory_rebuild, module)?)?;
    module.add_function(wrap_pyfunction!(memory_bindings::memory_sync, module)?)?;
    module.add_function(wrap_pyfunction!(memory_bindings::memory_overview, module)?)?;
    module.add_function(wrap_pyfunction!(
        memory_bindings::memory_schema_sql,
        module
    )?)?;
    module.add_function(wrap_pyfunction!(memory_bindings::memory_schema, module)?)?;
    module.add_function(wrap_pyfunction!(
        memory_bindings::memory_relation_schema,
        module
    )?)?;
    module.add_function(wrap_pyfunction!(memory_bindings::memory_query, module)?)?;
    Ok(())
}
