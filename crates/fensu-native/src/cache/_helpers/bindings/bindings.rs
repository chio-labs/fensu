//! Python-facing native cache operations.

use std::path::PathBuf;

use pyo3::types::{PyAnyMethods, PyBytes, PyList};
use pyo3::{pyfunction, Bound, Py, PyAny, PyResult, Python};

use crate::cache::_helpers::generation_bindings::{
    plan_generation_request, publish_generation_request, replay_generation_request,
    store_check_output_request, PlanGenerationRequest, PublishGenerationRequest,
    ReplayGenerationRequest, StoreCheckOutputRequest,
};
use crate::cache::_helpers::records::{decode_record, encode_record, value_to_python};
use crate::cache::_helpers::storage::{mutate_records, read_records, write_records};
use crate::cache::models::{CacheMetrics, CacheMutation, DecodedRecord, EncodedWrite};
use crate::cache::types::{
    GenerationPlanRow, MetricsRow, MutationRow, PublicationRow, PythonRecord, ReplayRow,
};

struct EncodeRecordRequest<'a, 'py> {
    py: Python<'py>,
    kind: &'a str,
    payload: &'a Bound<'py, PyAny>,
    payload_is_validated: bool,
    maximum_decoded_bytes: usize,
}

struct MutateBatchRequest<'a, 'py> {
    py: Python<'py>,
    repo_root: PathBuf,
    reads: Vec<(String, String)>,
    maximum_decoded_bytes: usize,
    mutate: Py<PyAny>,
    callback_error: &'a mut Option<pyo3::PyErr>,
}

macro_rules! define_cache_python_bindings {
    () => {
        #[pyfunction]
        pub(crate) fn cache_encode_record<'py>(
            py: Python<'py>,
            kind: &str,
            payload: &Bound<'py, PyAny>,
            payload_is_validated: bool,
            maximum_decoded_bytes: usize,
        ) -> PyResult<Bound<'py, PyBytes>> {
            encode_record_request(EncodeRecordRequest {
                py,
                kind,
                payload,
                payload_is_validated,
                maximum_decoded_bytes,
            })
        }

        #[pyfunction]
        pub(crate) fn cache_mutate_batch(
            py: Python<'_>,
            repo_root: PathBuf,
            reads: Vec<(String, String)>,
            maximum_decoded_bytes: usize,
            mutate: Py<PyAny>,
        ) -> PyResult<(bool, bool, MetricsRow)> {
            let mut callback_error = None;
            mutate_batch_request(MutateBatchRequest {
                py,
                repo_root,
                reads,
                maximum_decoded_bytes,
                mutate,
                callback_error: &mut callback_error,
            })
        }

        #[pyfunction]
        pub(crate) fn cache_replay_generation(
            py: Python<'_>,
            repo_root: PathBuf,
            global_fingerprint: String,
            targets: Vec<(String, Option<String>)>,
            maximum_decoded_bytes: usize,
        ) -> (Option<ReplayRow>, MetricsRow) {
            replay_generation_request(ReplayGenerationRequest {
                py,
                repo_root,
                global_fingerprint,
                targets,
                maximum_decoded_bytes,
            })
        }

        #[pyfunction]
        pub(crate) fn cache_plan_generation(
            py: Python<'_>,
            repo_root: PathBuf,
            global_fingerprint: String,
            targets: Vec<(String, Option<String>)>,
            allow_edit: bool,
            maximum_decoded_bytes: usize,
        ) -> PyResult<(Option<GenerationPlanRow>, MetricsRow)> {
            plan_generation_request(PlanGenerationRequest {
                py,
                repo_root,
                global_fingerprint,
                targets,
                allow_edit,
                maximum_decoded_bytes,
            })
        }

        #[pyfunction]
        pub(crate) fn cache_publish_generation(
            py: Python<'_>,
            repo_root: PathBuf,
            global_fingerprint: String,
            expected_index_fingerprint: Option<String>,
            retained_entries: Vec<(String, String, String, String)>,
            evaluations: &Bound<'_, PyList>,
            options: (bool, usize),
        ) -> PyResult<(PublicationRow, MetricsRow)> {
            publish_generation_request(PublishGenerationRequest {
                py,
                repo_root,
                global_fingerprint,
                expected_index_fingerprint,
                retained_entries,
                evaluations,
                options,
            })
        }

        #[pyfunction]
        pub(crate) fn cache_store_check_output(
            py: Python<'_>,
            repo_root: PathBuf,
            global_fingerprint: String,
            expected_index_fingerprint: String,
            surface: (Vec<String>, String, String, i64),
            maximum_decoded_bytes: usize,
        ) -> (bool, MetricsRow) {
            store_check_output_request(StoreCheckOutputRequest {
                py,
                repo_root,
                global_fingerprint,
                expected_index_fingerprint,
                surface,
                maximum_decoded_bytes,
            })
        }
    };
}

define_cache_python_bindings!();

fn encode_record_request<'py>(
    request: EncodeRecordRequest<'_, 'py>,
) -> PyResult<Bound<'py, PyBytes>> {
    let EncodeRecordRequest {
        py,
        kind,
        payload,
        payload_is_validated,
        maximum_decoded_bytes,
    } = request;
    let encoded = encode_record(kind, payload, payload_is_validated, maximum_decoded_bytes)?;
    Ok(PyBytes::new(py, &encoded))
}

#[pyfunction]
pub(crate) fn cache_decode_record(
    py: Python<'_>,
    data: Vec<u8>,
    expected_kind: &str,
    maximum_decoded_bytes: usize,
) -> PyResult<PythonRecord> {
    decoded_to_python(
        py,
        decode_record(&data, expected_kind, maximum_decoded_bytes),
    )
}

#[pyfunction]
pub(crate) fn cache_read_batch(
    py: Python<'_>,
    repo_root: PathBuf,
    reads: Vec<(String, String)>,
    maximum_decoded_bytes: usize,
) -> PyResult<(bool, Vec<PythonRecord>, MetricsRow)> {
    let outcome = py.detach({
        let repo_root = repo_root.clone();
        let reads = reads.clone();
        move || read_records(&repo_root, &reads, maximum_decoded_bytes)
    });
    let Some((records, metrics)) = outcome else {
        return Ok((
            false,
            std::iter::repeat_with(|| None).take(reads.len()).collect(),
            metrics_row(&CacheMetrics::default()),
        ));
    };
    let python_records = records
        .into_iter()
        .map(|record| decoded_to_python(py, record))
        .collect::<PyResult<Vec<_>>>()?;
    Ok((true, python_records, metrics_row(&metrics)))
}

#[pyfunction]
pub(crate) fn cache_write_batch(
    py: Python<'_>,
    repo_root: PathBuf,
    writes: Vec<(String, String, Vec<u8>, bool)>,
) -> (bool, MetricsRow) {
    let prepared = prepare_writes(writes);
    let outcome = py.detach(move || write_records(&repo_root, &prepared));
    match outcome {
        Some(metrics) => (true, metrics_row(&metrics)),
        None => (false, metrics_row(&CacheMetrics::default())),
    }
}

fn mutate_batch_request(request: MutateBatchRequest<'_, '_>) -> PyResult<(bool, bool, MetricsRow)> {
    let MutateBatchRequest {
        py,
        repo_root,
        reads,
        maximum_decoded_bytes,
        mutate,
        callback_error,
    } = request;
    let outcome = mutate_records(&repo_root, &reads, maximum_decoded_bytes, |records| {
        let python_records = records
            .into_iter()
            .map(|record| decoded_to_python(py, record))
            .collect::<PyResult<Vec<_>>>();
        let python_records = match python_records {
            Ok(records) => records,
            Err(error) => {
                *callback_error = Some(error);
                return Err(());
            }
        };
        let result = mutate.call1(py, (python_records,));
        let result = match result {
            Ok(result) => result,
            Err(error) => {
                *callback_error = Some(error);
                return Err(());
            }
        };
        if result.bind(py).is_none() {
            return Ok(None);
        }
        let mutation = match result.extract::<MutationRow>(py) {
            Ok(mutation) => mutation,
            Err(error) => {
                *callback_error = Some(error);
                return Err(());
            }
        };
        Ok(Some(CacheMutation {
            writes: prepare_writes(mutation.0),
            swept_prefix: mutation.1,
            retained_paths: mutation.2,
            deleted_paths: mutation.3,
        }))
    });
    if let Some(error) = callback_error.take() {
        return Err(error);
    }
    match outcome {
        Some((mutation, metrics)) => Ok((true, mutation.is_some(), metrics_row(&metrics))),
        None => Ok((false, false, metrics_row(&CacheMetrics::default()))),
    }
}

fn prepare_writes(writes: Vec<(String, String, Vec<u8>, bool)>) -> Vec<EncodedWrite> {
    writes
        .into_iter()
        .map(|(key, kind, data, insert_only)| EncodedWrite {
            key,
            kind,
            data,
            insert_only,
        })
        .collect()
}

fn decoded_to_python(py: Python<'_>, record: Option<DecodedRecord>) -> PyResult<PythonRecord> {
    record
        .map(|record| {
            Ok((
                record.kind,
                value_to_python(py, record.payload)?,
                record.fingerprint,
            ))
        })
        .transpose()
}

pub(super) fn metrics_row(metrics: &CacheMetrics) -> MetricsRow {
    (
        metrics.reads,
        metrics.bytes_read,
        metrics.writes,
        metrics.bytes_written,
        metrics.scans,
        metrics.deletes,
    )
}
