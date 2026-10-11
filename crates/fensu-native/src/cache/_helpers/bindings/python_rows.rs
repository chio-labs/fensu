//! Named cache boundary rows preserving the positional Python protocol.

use pyo3::{Py, PyAny};

macro_rules! python_tuple_row {
    ($name:ident { $($field:ident: $field_type:ty),+ $(,)? }) => {
        pub(crate) struct $name {
            $(pub(crate) $field: $field_type,)+
        }

        impl<'a, 'py> pyo3::FromPyObject<'a, 'py> for $name {
            type Error = pyo3::PyErr;

            fn extract(object: pyo3::Borrowed<'a, 'py, pyo3::PyAny>) -> pyo3::PyResult<Self> {
                let ($($field,)+) = object.extract()?;
                Ok(Self { $($field,)+ })
            }
        }

        impl<'py> pyo3::IntoPyObject<'py> for $name {
            type Target = pyo3::types::PyTuple;
            type Output = pyo3::Bound<'py, Self::Target>;
            type Error = pyo3::PyErr;

            fn into_pyobject(self, py: pyo3::Python<'py>) -> pyo3::PyResult<Self::Output> {
                ($(self.$field,)+).into_pyobject(py)
            }
        }
    };
}

python_tuple_row!(WriteRow {
    key: String,
    kind: String,
    data: Vec<u8>,
    insert_only: bool,
});
python_tuple_row!(MutationRow {
    writes: Vec<WriteRow>,
    swept_prefix: Option<String>,
    retained_paths: Vec<String>,
    deleted_paths: Vec<String>,
});
python_tuple_row!(MetricsRow {
    reads: usize,
    bytes_read: usize,
    writes: usize,
    bytes_written: usize,
    scans: usize,
    deletes: usize,
});
python_tuple_row!(ReplayRow {
    targets: Vec<String>,
    plain_output: String,
    color_output: String,
    exit_code: i64,
    index_fingerprint: String,
});
python_tuple_row!(IndexEntryRow {
    subject_kind: String,
    subject_identity: String,
    source_fingerprint: String,
    result_fingerprint: String,
    record_fingerprint: String,
});
python_tuple_row!(GenerationPlanRow {
    mode: String,
    index_fingerprint: Option<String>,
    entries: Vec<IndexEntryRow>,
    results: Vec<Py<PyAny>>,
    contributions: Vec<Py<PyAny>>,
    miss_paths: Vec<String>,
    hits: usize,
    misses: usize,
    invalidations: usize,
});
python_tuple_row!(PublicationRow {
    writes: usize,
    non_cacheable: usize,
    storage_failed: bool,
    internal_error: bool,
    index_fingerprint: Option<String>,
});
python_tuple_row!(CheckOutputRow {
    targets: Vec<String>,
    plain_output: String,
    color_output: String,
    exit_code: i64,
});
