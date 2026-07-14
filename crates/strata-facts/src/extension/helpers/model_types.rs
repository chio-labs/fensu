//! Access to the Python fact model constructors.

use pyo3::types::PyAnyMethods;
use pyo3::{Bound, PyAny, PyResult, Python};

use crate::constants;

pub(crate) fn model_type<'py>(py: Python<'py>, name: &str) -> PyResult<Bound<'py, PyAny>> {
    py.import(constants::MODELS_MODULE_NAME)?.getattr(name)
}
