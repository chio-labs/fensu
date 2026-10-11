//! Python conversion and dispatch for cached generation operations.

use std::path::PathBuf;

use pyo3::types::{PyList, PyListMethods};
use pyo3::{Bound, PyResult, Python};

use crate::cache::_helpers::bindings::metrics_row;
use crate::cache::_helpers::generation::{plan_generation, GenerationRequest};
use crate::cache::_helpers::publication::{
    prepare_publication, publish_generation, store_check_output, PublicationRequest,
};
use crate::cache::_helpers::python_rows::{
    CheckOutputRow, GenerationPlanRow, IndexEntryRow, MetricsRow, PublicationRow, ReplayRow,
};
use crate::cache::_helpers::records::{canonical_from_python, value_to_python};
use crate::cache::main::_dependency_kinds::dependency_kinds;
use crate::cache::main::_replay_generation::replay_generation;
use crate::cache::models::{CacheMetrics, CanonicalValue, CheckOutput, NativeIndexEntry};

pub(crate) struct ReplayGenerationRequest<'py> {
    pub(crate) py: Python<'py>,
    pub(crate) repo_root: PathBuf,
    pub(crate) global_fingerprint: String,
    pub(crate) targets: Vec<(String, String, Option<String>)>,
    pub(crate) tree_snapshot: Option<CanonicalValue>,
    pub(crate) maximum_decoded_bytes: usize,
}

pub(crate) struct DependencyKindsRequest<'py> {
    pub(crate) py: Python<'py>,
    pub(crate) repo_root: PathBuf,
    pub(crate) global_fingerprint: String,
    pub(crate) targets: Vec<(String, String, Option<String>)>,
    pub(crate) maximum_decoded_bytes: usize,
}

pub(crate) struct PlanGenerationRequest<'py> {
    pub(crate) py: Python<'py>,
    pub(crate) repo_root: PathBuf,
    pub(crate) global_fingerprint: String,
    pub(crate) targets: Vec<(String, String, Option<String>)>,
    pub(crate) tree_snapshot: Option<CanonicalValue>,
    pub(crate) allow_edit: bool,
    pub(crate) maximum_decoded_bytes: usize,
}

pub(crate) struct PublishGenerationRequest<'a, 'py> {
    pub(crate) py: Python<'py>,
    pub(crate) repo_root: PathBuf,
    pub(crate) global_fingerprint: String,
    pub(crate) expected_index_fingerprint: Option<String>,
    pub(crate) retained_entries: Vec<IndexEntryRow>,
    pub(crate) evaluations: &'a Bound<'py, PyList>,
    pub(crate) options: (bool, usize),
}

pub(crate) struct StoreCheckOutputRequest<'py> {
    pub(crate) py: Python<'py>,
    pub(crate) repo_root: PathBuf,
    pub(crate) global_fingerprint: String,
    pub(crate) expected_index_fingerprint: String,
    pub(crate) surface: CheckOutputRow,
    pub(crate) maximum_decoded_bytes: usize,
}

pub(super) fn replay_generation_request(
    request: ReplayGenerationRequest<'_>,
) -> (Option<ReplayRow>, MetricsRow) {
    let ReplayGenerationRequest {
        py,
        repo_root,
        global_fingerprint,
        targets,
        tree_snapshot,
        maximum_decoded_bytes,
    } = request;
    let outcome = py.detach(move || {
        replay_generation(crate::cache::_helpers::replay::ReplayGenerationRequest {
            repo_root: &repo_root,
            global_fingerprint: &global_fingerprint,
            targets: &targets,
            tree_snapshot: tree_snapshot.as_ref(),
            maximum_decoded_bytes,
        })
    });
    let Some((replay, metrics)) = outcome else {
        return (None, metrics_row(&CacheMetrics::default()));
    };
    (
        Some(ReplayRow {
            targets: replay.targets,
            plain_output: replay.plain_output,
            color_output: replay.color_output,
            exit_code: replay.exit_code,
            index_fingerprint: replay.index_fingerprint,
        }),
        metrics_row(&metrics),
    )
}

pub(super) fn dependency_kinds_request(
    request: DependencyKindsRequest<'_>,
) -> (Option<Vec<String>>, MetricsRow) {
    let DependencyKindsRequest {
        py,
        repo_root,
        global_fingerprint,
        targets,
        maximum_decoded_bytes,
    } = request;
    let outcome = py.detach(move || {
        dependency_kinds(
            &repo_root,
            &global_fingerprint,
            &targets,
            maximum_decoded_bytes,
        )
    });
    match outcome {
        Some((kinds, metrics)) => (Some(kinds), metrics_row(&metrics)),
        None => (None, metrics_row(&CacheMetrics::default())),
    }
}

pub(super) fn plan_generation_request(
    request: PlanGenerationRequest<'_>,
) -> PyResult<(Option<GenerationPlanRow>, MetricsRow)> {
    let PlanGenerationRequest {
        py,
        repo_root,
        global_fingerprint,
        targets,
        tree_snapshot,
        allow_edit,
        maximum_decoded_bytes,
    } = request;
    let outcome = py.detach(move || {
        plan_generation(GenerationRequest {
            repo_root: &repo_root,
            global_fingerprint: &global_fingerprint,
            targets: &targets,
            tree_snapshot: tree_snapshot.as_ref(),
            allow_edit,
            maximum_decoded_bytes,
        })
    });
    let Some((plan, metrics)) = outcome else {
        return Ok((None, metrics_row(&CacheMetrics::default())));
    };
    let results = plan
        .cached_results
        .into_iter()
        .map(|value| value_to_python(py, value))
        .collect::<PyResult<Vec<_>>>()?;
    let contributions = plan
        .contributions
        .into_iter()
        .map(|value| value_to_python(py, value))
        .collect::<PyResult<Vec<_>>>()?;
    let entries: Vec<IndexEntryRow> = plan
        .entries
        .into_iter()
        .map(|entry| IndexEntryRow {
            subject_kind: entry.subject_kind,
            subject_identity: entry.subject_identity,
            source_fingerprint: entry.source_fingerprint,
            result_fingerprint: entry.result_fingerprint,
            record_fingerprint: entry.record_fingerprint,
        })
        .collect();
    Ok((
        Some(GenerationPlanRow {
            mode: plan.mode,
            index_fingerprint: plan.index_fingerprint,
            entries,
            results,
            contributions,
            miss_paths: plan.miss_paths,
            hits: plan.hits,
            misses: plan.misses,
            invalidations: plan.invalidations,
        }),
        metrics_row(&metrics),
    ))
}

pub(super) fn publish_generation_request(
    request: PublishGenerationRequest<'_, '_>,
) -> PyResult<(PublicationRow, MetricsRow)> {
    let PublishGenerationRequest {
        py,
        repo_root,
        global_fingerprint,
        expected_index_fingerprint,
        retained_entries,
        evaluations,
        options,
    } = request;
    let (retain_all_observations, maximum_decoded_bytes) = options;
    let values = evaluations
        .iter()
        .map(|value| canonical_from_python(&value))
        .collect::<PyResult<Vec<_>>>()?;
    let request = PublicationRequest {
        global_fingerprint,
        expected_index_fingerprint,
        retained_entries: retained_entries
            .into_iter()
            .map(
                |IndexEntryRow {
                     subject_kind,
                     subject_identity,
                     source_fingerprint,
                     result_fingerprint,
                     record_fingerprint,
                 }| {
                    NativeIndexEntry {
                        subject_kind,
                        subject_identity,
                        source_fingerprint,
                        result_fingerprint,
                        record_fingerprint,
                    }
                },
            )
            .collect(),
        preparation: prepare_publication(values),
        retain_all_observations,
        maximum_decoded_bytes,
    };
    let (result, metrics) = py.detach(move || publish_generation(&repo_root, request));
    Ok((
        PublicationRow {
            writes: result.writes,
            non_cacheable: result.non_cacheable,
            storage_failed: result.storage_failed,
            internal_error: result.internal_error,
            index_fingerprint: result.index_fingerprint,
        },
        metrics_row(&metrics),
    ))
}

pub(super) fn store_check_output_request(
    request: StoreCheckOutputRequest<'_>,
) -> (bool, MetricsRow) {
    let StoreCheckOutputRequest {
        py,
        repo_root,
        global_fingerprint,
        expected_index_fingerprint,
        surface,
        maximum_decoded_bytes,
    } = request;
    let CheckOutputRow {
        targets,
        plain_output,
        color_output,
        exit_code,
    } = surface;
    let outcome = py.detach(move || {
        store_check_output(
            &repo_root,
            (&global_fingerprint, &expected_index_fingerprint),
            CheckOutput {
                targets: &targets,
                plain_output: &plain_output,
                color_output: &color_output,
                exit_code,
            },
            maximum_decoded_bytes,
        )
    });
    match outcome {
        Some(metrics) => (true, metrics_row(&metrics)),
        None => (false, metrics_row(&CacheMetrics::default())),
    }
}
