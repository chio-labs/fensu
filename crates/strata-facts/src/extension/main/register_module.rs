//! Register the strata_facts Python module surface.

use pyo3::pymodule;
use pyo3::types::{PyModule, PyModuleMethods};
use pyo3::wrap_pyfunction;
use pyo3::{Bound, PyResult};

use crate::extension::helpers::bindings;

/// Expose the native fact-extraction functions to Python.
#[pymodule]
pub fn strata_facts(module: &Bound<'_, PyModule>) -> PyResult<()> {
    module.add_function(wrap_pyfunction!(bindings::backend_version, module)?)?;
    module.add_function(wrap_pyfunction!(bindings::check_syntax, module)?)?;
    module.add_function(wrap_pyfunction!(bindings::locate_byte_offset, module)?)?;
    Ok(())
}
