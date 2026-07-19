//! Native cache boundary type declarations.

use pyo3::{Py, PyAny};

pub(crate) type PythonRecord = Option<(String, Py<PyAny>, String)>;
pub(crate) type MutationRow = (
    Vec<(String, String, Vec<u8>, bool)>,
    Option<String>,
    Vec<String>,
    Vec<String>,
);
pub(crate) type MetricsRow = (usize, usize, usize, usize, usize, usize);
pub(crate) type ReplayRow = (Vec<String>, String, String, i64, String);
pub(crate) type IndexEntryRow = (String, String, String, String);
pub(crate) type GenerationPlanRow = (
    String,
    Option<String>,
    Vec<IndexEntryRow>,
    Vec<Py<PyAny>>,
    Vec<Py<PyAny>>,
    Vec<String>,
    usize,
    usize,
    usize,
);
pub(crate) type PublicationRow = (usize, usize, bool, bool, Option<String>);
