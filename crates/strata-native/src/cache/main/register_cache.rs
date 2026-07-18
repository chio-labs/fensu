//! Register native persistent-cache extension functions.

use pyo3::types::{PyModule, PyModuleMethods};
use pyo3::{wrap_pyfunction, Bound, PyResult};

use crate::cache::helpers::bindings;

pub(crate) fn register_cache_functions(module: &Bound<'_, PyModule>) -> PyResult<()> {
    module.add_function(wrap_pyfunction!(bindings::cache_encode_record, module)?)?;
    module.add_function(wrap_pyfunction!(bindings::cache_decode_record, module)?)?;
    module.add_function(wrap_pyfunction!(bindings::cache_read_batch, module)?)?;
    module.add_function(wrap_pyfunction!(bindings::cache_write_batch, module)?)?;
    module.add_function(wrap_pyfunction!(bindings::cache_mutate_batch, module)?)?;
    module.add_function(wrap_pyfunction!(bindings::cache_replay_generation, module)?)?;
    Ok(())
}
