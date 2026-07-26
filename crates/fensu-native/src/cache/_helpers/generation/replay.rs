//! Native complete-generation validation and rendered-output replay.

use std::collections::HashMap;
use std::path::Path;

use fensu_facts::snapshot::main::build_repository_observation_index::build_repository_observation_index;
use fensu_facts::snapshot::models::{
    RepositoryObservationAnswer, RepositoryObservationQuery, RepositoryObservationState,
};

use crate::cache::_helpers::schema::{
    decode_index, decode_observations, metadata_is_current, observation_map,
};
use crate::cache::_helpers::schema_values::exact_fields;
use crate::cache::_helpers::storage::read_records;
use crate::cache::models::{
    CacheMetrics, CanonicalValue, DecodedRecord, NativeDependencyKey, NativeDependencyObservation,
    NativeIndexEntry, NativeReplay,
};

const REPLAY_HEADER_READS: [(&str, &str); 2] =
    [("metadata.json", "metadata"), ("index.json", "index")];
const REPLAY_BODY_READS: [(&str, &str); 2] = [
    ("output.json", "check_output"),
    ("dependencies.json", "dependencies"),
];

pub(crate) fn build_replay_generation(
    repo_root: &Path,
    global_fingerprint: &str,
    targets: &[(String, Option<String>)],
    maximum_decoded_bytes: usize,
) -> Option<(NativeReplay, CacheMetrics)> {
    let reads = REPLAY_HEADER_READS
        .iter()
        .map(|(path, kind)| ((*path).to_owned(), (*kind).to_owned()))
        .collect::<Vec<_>>();
    let (records, mut metrics) = read_records(repo_root, &reads, maximum_decoded_bytes)?;
    let mut records = records.into_iter();
    let metadata = records.next()??;
    let index = records.next()??;
    if !metadata_is_current(&metadata, global_fingerprint) {
        return None;
    }
    let (entries, dependencies_fingerprint, _) = decode_index(&index, global_fingerprint)?;
    current_manifest(&entries, targets)?;
    let reads = REPLAY_BODY_READS
        .iter()
        .map(|(path, kind)| ((*path).to_owned(), (*kind).to_owned()))
        .collect::<Vec<_>>();
    let (records, body_metrics) = read_records(repo_root, &reads, maximum_decoded_bytes)?;
    metrics.merge(&body_metrics);
    let mut records = records.into_iter();
    let output = records.next()??;
    let dependencies = records.next()??;
    if Some(dependencies.fingerprint.as_str()) != dependencies_fingerprint.as_deref() {
        return None;
    }
    let replay = current_output(&output, global_fingerprint, &index.fingerprint, targets)?;
    let observations = decode_observations(&dependencies)?;
    let indexed = observation_map(&observations)?;
    observations_are_current(repo_root, &indexed).then_some((replay, metrics))
}

fn current_manifest(
    entries: &[NativeIndexEntry],
    targets: &[(String, Option<String>)],
) -> Option<()> {
    if entries.len() != targets.len() {
        return None;
    }
    for (entry, (target_path, target_fingerprint)) in entries.iter().zip(targets) {
        let fingerprint = target_fingerprint.as_ref()?;
        if entry.path != *target_path || entry.source_fingerprint != *fingerprint {
            return None;
        }
    }
    Some(())
}

fn current_output(
    record: &DecodedRecord,
    global_fingerprint: &str,
    index_fingerprint: &str,
    targets: &[(String, Option<String>)],
) -> Option<NativeReplay> {
    let payload = &record.payload;
    if !exact_fields(
        payload,
        &[
            "color_output",
            "exit_code",
            "global_fingerprint",
            "index_fingerprint",
            "plain_output",
            "targets",
        ],
    ) || payload.field("global_fingerprint")?.as_str()? != global_fingerprint
        || payload.field("index_fingerprint")?.as_str()? != index_fingerprint
    {
        return None;
    }
    let output_targets = string_list(payload.field("targets")?)?;
    let expected_targets = targets
        .iter()
        .map(|(path, _)| path.clone())
        .collect::<Vec<_>>();
    if output_targets != expected_targets {
        return None;
    }
    Some(NativeReplay {
        targets: output_targets,
        plain_output: payload.field("plain_output")?.as_str()?.to_owned(),
        color_output: payload.field("color_output")?.as_str()?.to_owned(),
        exit_code: payload.field("exit_code")?.as_nonnegative_i64()?,
        index_fingerprint: index_fingerprint.to_owned(),
    })
}

fn string_list(value: &CanonicalValue) -> Option<Vec<String>> {
    value
        .as_list()?
        .iter()
        .map(|item| item.as_str().map(str::to_owned))
        .collect()
}

fn observations_are_current(
    repo_root: &Path,
    observations: &HashMap<NativeDependencyKey, NativeDependencyObservation>,
) -> bool {
    let current = observe_dependencies(repo_root, observations);
    current.len() == observations.len() && current.values().all(|value| *value)
}

pub(super) fn observe_dependencies(
    repo_root: &Path,
    observations: &HashMap<NativeDependencyKey, NativeDependencyObservation>,
) -> HashMap<NativeDependencyKey, bool> {
    let queries = observations
        .keys()
        .map(|key| RepositoryObservationQuery {
            relative_path: key.query_path.clone(),
            kind: key.kind.clone(),
            pattern: key.pattern.clone(),
            recursive: key.recursive,
        })
        .collect::<Vec<_>>();
    let Some(index) = build_repository_observation_index(repo_root, &queries) else {
        return HashMap::new();
    };
    queries
        .into_iter()
        .filter_map(|query| {
            let key = NativeDependencyKey {
                query_path: query.relative_path.clone(),
                kind: query.kind.clone(),
                pattern: query.pattern.clone(),
                recursive: query.recursive,
            };
            let expected = observations.get(&key)?;
            let current = query.observe(&index);
            Some((key, state_matches(current, expected)))
        })
        .collect()
}

fn state_matches(
    state: Option<RepositoryObservationState>,
    expected: &NativeDependencyObservation,
) -> bool {
    let Some(state) = state else {
        return false;
    };
    state.dependency_path == expected.dependency_path
        && match state.answer {
            RepositoryObservationAnswer::None => expected.answer.is_null(),
            RepositoryObservationAnswer::Bool(value) => expected.answer.as_bool() == Some(value),
            RepositoryObservationAnswer::String(value) => {
                expected.answer.as_str() == Some(value.as_str())
            }
            RepositoryObservationAnswer::Paths(paths) => {
                expected.answer.as_list().is_some_and(|items| {
                    items
                        .iter()
                        .map(CanonicalValue::as_str)
                        .eq(paths.iter().map(|path| Some(path.as_str())))
                })
            }
        }
}
