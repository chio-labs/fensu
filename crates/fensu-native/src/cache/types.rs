//! Native cache boundary type declarations.

use std::collections::HashMap;

use pyo3::{Py, PyAny};

pub(crate) type PythonRecord = Option<(String, Py<PyAny>, String)>;
pub(crate) type StoredRecordMap = HashMap<String, (String, Vec<u8>)>;
