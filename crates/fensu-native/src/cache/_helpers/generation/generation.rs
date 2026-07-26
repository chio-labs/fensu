//! Native generation loading, repository observation, and cache miss planning.

use std::collections::{HashMap, HashSet};
use std::path::Path;

use crate::cache::_helpers::replay::observe_dependencies;
use crate::cache::_helpers::schema::{
    decode_collection, decode_file_result_dependencies, decode_index, decode_observations,
    metadata_is_current, observation_map, resolved_file_payload,
};
use crate::cache::_helpers::storage::read_records;
use crate::cache::models::{
    CacheMetrics, CanonicalValue, NativeDependencyKey, NativeDependencyObservation,
    NativeGenerationPlan, NativeIndexEntry,
};

const GENERATION_READS: [(&str, &str); 4] = [
    ("metadata.json", "metadata"),
    ("index.json", "index"),
    ("dependencies.json", "dependencies"),
    ("collection.json", "collection"),
];
const RESULT_KIND: &str = "file_result";
const EDIT_MODE: &str = "edit";
const RESULT_MODE: &str = "results";
const COLD_MODE: &str = "cold";

struct ResultPlanInputs<'a> {
    targets: &'a [(String, Option<String>)],
    index_entries: &'a [NativeIndexEntry],
    source_equal: Vec<NativeIndexEntry>,
    records: Vec<Option<crate::cache::models::DecodedRecord>>,
    global_fingerprint: &'a str,
    observations: &'a HashMap<NativeDependencyKey, NativeDependencyObservation>,
    current: &'a HashMap<NativeDependencyKey, bool>,
    index_fingerprint: String,
}

pub(crate) struct GenerationRequest<'a> {
    pub repo_root: &'a Path,
    pub global_fingerprint: &'a str,
    pub targets: &'a [(String, Option<String>)],
    pub allow_edit: bool,
    pub maximum_decoded_bytes: usize,
}

struct EditPlanInputs<'a> {
    targets: &'a [(String, Option<String>)],
    index_entries: &'a [NativeIndexEntry],
    source_equal: &'a [NativeIndexEntry],
    collection: Vec<CanonicalValue>,
    index_fingerprint: String,
}

pub(crate) fn plan_generation(
    request: GenerationRequest<'_>,
) -> Option<(NativeGenerationPlan, CacheMetrics)> {
    let GenerationRequest {
        repo_root,
        global_fingerprint,
        targets,
        allow_edit,
        maximum_decoded_bytes,
    } = request;
    let reads = GENERATION_READS
        .iter()
        .map(|(path, kind)| ((*path).to_owned(), (*kind).to_owned()))
        .collect::<Vec<_>>();
    let (records, mut metrics) = read_records(repo_root, &reads, maximum_decoded_bytes)?;
    let mut records = records.into_iter();
    let metadata = records.next().flatten();
    let index_record = records.next().flatten();
    let dependencies_record = records.next().flatten();
    let collection_record = records.next().flatten();
    let (Some(metadata), Some(index_record)) = (metadata, index_record) else {
        return Some((cold_plan(targets), metrics));
    };
    if !metadata_is_current(&metadata, global_fingerprint) {
        return Some((cold_plan(targets), metrics));
    }
    let Some((index_entries, dependencies_fingerprint, collection_fingerprint)) =
        decode_index(&index_record, global_fingerprint)
    else {
        return Some((cold_plan(targets), metrics));
    };
    let observations =
        matching_observations(dependencies_record.as_ref(), dependencies_fingerprint);
    let observations_by_key = observations
        .as_deref()
        .and_then(observation_map)
        .unwrap_or_default();
    let current = observe_dependencies(repo_root, &observations_by_key);
    let collection = matching_collection(collection_record.as_ref(), collection_fingerprint);
    let entries_by_path = index_entries
        .iter()
        .map(|entry| (entry.path.as_str(), entry))
        .collect::<HashMap<_, _>>();
    let target_paths = targets
        .iter()
        .map(|(path, _)| path.as_str())
        .collect::<HashSet<_>>();
    let source_equal = targets
        .iter()
        .filter_map(|(path, fingerprint)| {
            let entry = entries_by_path.get(path.as_str())?;
            (fingerprint.as_deref() == Some(entry.source_fingerprint.as_str()))
                .then_some((*entry).clone())
        })
        .collect::<Vec<_>>();
    let changed = targets.len() != source_equal.len()
        || index_entries
            .iter()
            .any(|entry| !target_paths.contains(entry.path.as_str()));
    if allow_edit
        && changed
        && observations.is_some()
        && current.values().all(|value| *value)
        && collection.is_some()
    {
        return Some((
            edit_plan(EditPlanInputs {
                targets,
                index_entries: &index_entries,
                source_equal: &source_equal,
                collection: collection.unwrap_or_default(),
                index_fingerprint: index_record.fingerprint,
            }),
            metrics,
        ));
    }
    let result_reads = source_equal
        .iter()
        .map(|entry| {
            (
                result_path(&entry.result_fingerprint),
                RESULT_KIND.to_owned(),
            )
        })
        .collect::<Vec<_>>();
    let result_records = if result_reads.is_empty() {
        Vec::new()
    } else {
        let (records, result_metrics) =
            read_records(repo_root, &result_reads, maximum_decoded_bytes)?;
        metrics.merge(&result_metrics);
        records
    };
    let plan = result_plan(ResultPlanInputs {
        targets,
        index_entries: &index_entries,
        source_equal,
        records: result_records,
        global_fingerprint,
        observations: &observations_by_key,
        current: &current,
        index_fingerprint: index_record.fingerprint,
    });
    Some((plan, metrics))
}

fn result_plan(inputs: ResultPlanInputs<'_>) -> NativeGenerationPlan {
    let target_fingerprints = inputs
        .targets
        .iter()
        .map(|(path, fingerprint)| (path.as_str(), fingerprint.as_deref()))
        .collect::<HashMap<_, _>>();
    let existing = inputs
        .index_entries
        .iter()
        .map(|entry| (entry.path.as_str(), entry))
        .collect::<HashMap<_, _>>();
    let mut valid_entries = Vec::new();
    let mut cached_results = Vec::new();
    let mut invalid_dependency_paths = HashSet::new();
    let mut corrupt_paths = HashSet::new();
    for (entry, record) in inputs.source_equal.into_iter().zip(inputs.records) {
        let Some(record) = record else {
            corrupt_paths.insert(entry.path.clone());
            continue;
        };
        let Some(keys) = decode_file_result_dependencies(
            &record,
            &entry,
            inputs.global_fingerprint,
            inputs.observations,
        ) else {
            corrupt_paths.insert(entry.path.clone());
            continue;
        };
        if keys
            .iter()
            .any(|key| inputs.current.get(key).copied() != Some(true))
        {
            invalid_dependency_paths.insert(entry.path.clone());
            continue;
        }
        let Some(payload) =
            resolved_file_payload(&record.payload, &entry.path, &keys, inputs.observations)
        else {
            corrupt_paths.insert(entry.path.clone());
            continue;
        };
        valid_entries.push(entry);
        cached_results.push(payload);
    }
    let valid_paths = valid_entries
        .iter()
        .map(|entry| entry.path.as_str())
        .collect::<HashSet<_>>();
    let hits = valid_paths.len();
    let miss_paths = inputs
        .targets
        .iter()
        .filter_map(|(path, _)| (!valid_paths.contains(path.as_str())).then_some(path.clone()))
        .collect::<Vec<_>>();
    let misses = miss_paths
        .iter()
        .filter(|path| !existing.contains_key(path.as_str()) || corrupt_paths.contains(*path))
        .count();
    let source_invalidations = inputs
        .targets
        .iter()
        .filter(|(path, fingerprint)| {
            existing.get(path.as_str()).is_some_and(|entry| {
                fingerprint.as_deref() != Some(entry.source_fingerprint.as_str())
            })
        })
        .count();
    let deleted = inputs
        .index_entries
        .iter()
        .filter(|entry| !target_fingerprints.contains_key(entry.path.as_str()))
        .count();
    NativeGenerationPlan {
        mode: RESULT_MODE.to_owned(),
        index_fingerprint: Some(inputs.index_fingerprint),
        entries: valid_entries,
        cached_results,
        contributions: Vec::new(),
        miss_paths,
        hits,
        misses,
        invalidations: source_invalidations + invalid_dependency_paths.len() + deleted,
    }
}

fn edit_plan(inputs: EditPlanInputs<'_>) -> NativeGenerationPlan {
    let EditPlanInputs {
        targets,
        index_entries,
        source_equal,
        collection,
        index_fingerprint,
    } = inputs;
    let retained_paths = source_equal
        .iter()
        .map(|entry| entry.path.as_str())
        .collect::<HashSet<_>>();
    let existing_paths = index_entries
        .iter()
        .map(|entry| entry.path.as_str())
        .collect::<HashSet<_>>();
    let target_paths = targets
        .iter()
        .map(|(path, _)| path.as_str())
        .collect::<HashSet<_>>();
    let contributions = collection
        .into_iter()
        .filter(|value| {
            value
                .field("path")
                .and_then(CanonicalValue::as_str)
                .is_some_and(|path| retained_paths.contains(path))
        })
        .collect();
    let miss_paths = targets
        .iter()
        .filter_map(|(path, _)| (!retained_paths.contains(path.as_str())).then_some(path.clone()))
        .collect::<Vec<_>>();
    let misses = miss_paths
        .iter()
        .filter(|path| !existing_paths.contains(path.as_str()))
        .count();
    let changed_invalidations = miss_paths.len() - misses;
    NativeGenerationPlan {
        mode: EDIT_MODE.to_owned(),
        index_fingerprint: Some(index_fingerprint),
        entries: source_equal.to_vec(),
        cached_results: Vec::new(),
        contributions,
        miss_paths,
        hits: source_equal.len(),
        misses,
        invalidations: changed_invalidations
            + index_entries
                .iter()
                .filter(|entry| !target_paths.contains(entry.path.as_str()))
                .count(),
    }
}

fn cold_plan(targets: &[(String, Option<String>)]) -> NativeGenerationPlan {
    NativeGenerationPlan {
        mode: COLD_MODE.to_owned(),
        index_fingerprint: None,
        entries: Vec::new(),
        cached_results: Vec::new(),
        contributions: Vec::new(),
        miss_paths: targets.iter().map(|(path, _)| path.clone()).collect(),
        hits: 0,
        misses: targets.len(),
        invalidations: 0,
    }
}

fn matching_observations(
    record: Option<&crate::cache::models::DecodedRecord>,
    expected_fingerprint: Option<String>,
) -> Option<Vec<NativeDependencyObservation>> {
    let record = record?;
    (Some(record.fingerprint.as_str()) == expected_fingerprint.as_deref())
        .then(|| decode_observations(record))?
}

fn matching_collection(
    record: Option<&crate::cache::models::DecodedRecord>,
    expected_fingerprint: Option<String>,
) -> Option<Vec<CanonicalValue>> {
    let record = record?;
    (Some(record.fingerprint.as_str()) == expected_fingerprint.as_deref())
        .then(|| decode_collection(record))?
}

fn result_path(fingerprint: &str) -> String {
    format!("results/{}/{}.json", &fingerprint[..2], fingerprint)
}
