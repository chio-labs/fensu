//! Retained dependency and collection merging for native generation publication.

use std::collections::{HashMap, HashSet};

use crate::cache::helpers::schema::{
    decode_collection, decode_file_result_dependencies, decode_index, decode_observations,
    metadata_is_current, observation_map,
};
use crate::cache::models::{
    CanonicalValue, DecodedRecord, NativeDependencyKey, NativeDependencyObservation,
    NativeIndexEntry, NativePublicationPreparation,
};

pub(crate) type IndexState = (Vec<NativeIndexEntry>, Option<String>, Option<String>);

pub(crate) fn current_index(
    metadata: Option<&DecodedRecord>,
    index: Option<&DecodedRecord>,
    global_fingerprint: &str,
) -> Option<IndexState> {
    metadata_is_current(metadata?, global_fingerprint)
        .then(|| decode_index(index?, global_fingerprint))?
}

pub(crate) fn matching_dependencies(
    record: Option<&DecodedRecord>,
    fingerprint: Option<&str>,
) -> Option<Vec<NativeDependencyObservation>> {
    let record = record?;
    (Some(record.fingerprint.as_str()) == fingerprint).then(|| decode_observations(record))?
}

pub(crate) fn retained_dependency_keys(
    entries: &[NativeIndexEntry],
    records: &[Option<DecodedRecord>],
    global_fingerprint: &str,
    observations: &[NativeDependencyObservation],
) -> Option<HashSet<NativeDependencyKey>> {
    let indexed = observation_map(observations)?;
    let mut retained = HashSet::new();
    for (entry, record) in entries.iter().zip(records) {
        let record = record.as_ref()?;
        let keys = decode_file_result_dependencies(record, entry, global_fingerprint, &indexed)?;
        retained.extend(keys);
    }
    Some(retained)
}

pub(crate) fn merged_observations(
    old: &[NativeDependencyObservation],
    retained_keys: Option<&HashSet<NativeDependencyKey>>,
    preparation: &NativePublicationPreparation,
) -> Option<Vec<NativeDependencyObservation>> {
    let mut merged = HashMap::new();
    for observation in old.iter().filter(|observation| {
        retained_keys
            .map(|keys| keys.contains(&observation.key))
            .unwrap_or(true)
    }) {
        merge_observation(&mut merged, observation.clone())?;
    }
    for candidate in &preparation.candidates {
        for observation in &candidate.observations {
            merge_observation(&mut merged, observation.clone())?;
        }
    }
    let mut values = merged.into_values().collect::<Vec<_>>();
    values.sort_by(|left, right| dependency_sort_key(left).cmp(&dependency_sort_key(right)));
    Some(values)
}

pub(crate) fn merged_contributions(
    existing: Option<&IndexState>,
    record: Option<&DecodedRecord>,
    retained_entries: &[NativeIndexEntry],
    preparation: &NativePublicationPreparation,
) -> Vec<CanonicalValue> {
    let expected = existing.and_then(|(_, _, fingerprint)| fingerprint.as_deref());
    let retained_paths = retained_entries
        .iter()
        .map(|entry| entry.path.as_str())
        .collect::<HashSet<_>>();
    let mut merged = record
        .filter(|record| Some(record.fingerprint.as_str()) == expected)
        .and_then(decode_collection)
        .unwrap_or_default()
        .into_iter()
        .filter_map(|value| {
            let path = value.field("path")?.as_str()?.to_owned();
            retained_paths
                .contains(path.as_str())
                .then_some((path, value))
        })
        .collect::<HashMap<_, _>>();
    for candidate in &preparation.candidates {
        if let Some(contribution) = &candidate.contribution {
            merged.insert(candidate.path.clone(), contribution.clone());
        }
    }
    let mut values = merged.into_iter().collect::<Vec<_>>();
    values.sort_by(|left, right| left.0.cmp(&right.0));
    values.into_iter().map(|(_, value)| value).collect()
}

pub(crate) fn index_payload(
    global_fingerprint: &str,
    entries: &[NativeIndexEntry],
    dependencies_fingerprint: &str,
    collection_fingerprint: &str,
) -> CanonicalValue {
    CanonicalValue::Object(vec![
        (
            "collection_fingerprint".to_owned(),
            CanonicalValue::String(collection_fingerprint.to_owned()),
        ),
        (
            "dependencies_fingerprint".to_owned(),
            CanonicalValue::String(dependencies_fingerprint.to_owned()),
        ),
        (
            "entries".to_owned(),
            CanonicalValue::List(entries.iter().map(index_entry_value).collect()),
        ),
        (
            "global_fingerprint".to_owned(),
            CanonicalValue::String(global_fingerprint.to_owned()),
        ),
    ])
}

fn merge_observation(
    merged: &mut HashMap<NativeDependencyKey, NativeDependencyObservation>,
    observation: NativeDependencyObservation,
) -> Option<()> {
    if let Some(existing) = merged.get_mut(&observation.key) {
        if existing.dependency_path != observation.dependency_path
            || existing.answer != observation.answer
        {
            return None;
        }
        if observation.requester_path < existing.requester_path {
            existing.requester_path = observation.requester_path;
        }
    } else {
        merged.insert(observation.key.clone(), observation);
    }
    Some(())
}

fn index_entry_value(entry: &NativeIndexEntry) -> CanonicalValue {
    CanonicalValue::Object(vec![
        (
            "path".to_owned(),
            CanonicalValue::String(entry.path.clone()),
        ),
        (
            "record_fingerprint".to_owned(),
            CanonicalValue::String(entry.record_fingerprint.clone()),
        ),
        (
            "result_fingerprint".to_owned(),
            CanonicalValue::String(entry.result_fingerprint.clone()),
        ),
        (
            "source_fingerprint".to_owned(),
            CanonicalValue::String(entry.source_fingerprint.clone()),
        ),
    ])
}

fn dependency_sort_key(observation: &NativeDependencyObservation) -> (&str, &str, &str, bool) {
    (
        &observation.key.query_path,
        &observation.key.kind,
        observation.key.pattern.as_deref().unwrap_or(""),
        observation.key.recursive,
    )
}
