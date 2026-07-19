//! Semantic decoding for native persistent result generations.

use std::collections::{HashMap, HashSet};

use sha2::{Digest, Sha256};

use crate::cache::constants::DEPENDENCIES_FIELD;
use crate::cache::helpers::schema_values::{
    decode_exceptions, decode_faults, decode_threshold_uses, exact_fields, optional_fingerprint,
    optional_string, valid_contribution, valid_dependency_shape, valid_fingerprint,
    valid_relative_path,
};
use crate::cache::models::{
    CanonicalValue, DecodedRecord, NativeDependencyKey, NativeDependencyObservation,
    NativeIndexEntry, NativePublicationCandidate,
};

const FILE_RESULT_DOMAIN: &[u8] = b"strata-file-result-v2\0";
pub(crate) fn metadata_is_current(record: &DecodedRecord, global_fingerprint: &str) -> bool {
    exact_fields(&record.payload, &["global_fingerprint"])
        && record
            .payload
            .field("global_fingerprint")
            .and_then(CanonicalValue::as_str)
            == Some(global_fingerprint)
        && valid_fingerprint(global_fingerprint)
}
pub(crate) fn decode_index(
    record: &DecodedRecord,
    global_fingerprint: &str,
) -> Option<(Vec<NativeIndexEntry>, Option<String>, Option<String>)> {
    let payload = &record.payload;
    if !exact_fields(
        payload,
        &[
            "collection_fingerprint",
            "dependencies_fingerprint",
            "entries",
            "global_fingerprint",
        ],
    ) || payload.field("global_fingerprint")?.as_str()? != global_fingerprint
    {
        return None;
    }
    let dependencies = optional_fingerprint(payload.field("dependencies_fingerprint")?)?;
    let collection = optional_fingerprint(payload.field("collection_fingerprint")?)?;
    let mut entries = Vec::new();
    let mut previous: Option<String> = None;
    for value in payload.field("entries")?.as_list()? {
        let entry = decode_index_entry(value)?;
        if previous
            .as_deref()
            .is_some_and(|path| path >= entry.path.as_str())
        {
            return None;
        }
        previous = Some(entry.path.clone());
        entries.push(entry);
    }
    Some((entries, dependencies, collection))
}
pub(crate) fn decode_observations(
    record: &DecodedRecord,
) -> Option<Vec<NativeDependencyObservation>> {
    if !exact_fields(&record.payload, &["observations"]) {
        return None;
    }
    record
        .payload
        .field("observations")?
        .as_list()?
        .iter()
        .map(decode_observation)
        .collect()
}
pub(crate) fn decode_collection(record: &DecodedRecord) -> Option<Vec<CanonicalValue>> {
    if !exact_fields(&record.payload, &["contributions"]) {
        return None;
    }
    let mut previous: Option<String> = None;
    let mut decoded = Vec::new();
    for value in record.payload.field("contributions")?.as_list()? {
        let path = valid_contribution(value)?;
        if previous.as_deref().is_some_and(|prior| prior >= path) {
            return None;
        }
        previous = Some(path.to_owned());
        decoded.push(value.clone());
    }
    Some(decoded)
}
pub(crate) fn decode_file_result_dependencies(
    record: &DecodedRecord,
    entry: &NativeIndexEntry,
    global_fingerprint: &str,
    observations: &HashMap<NativeDependencyKey, NativeDependencyObservation>,
) -> Option<Vec<NativeDependencyKey>> {
    if record.fingerprint != entry.record_fingerprint
        || file_result_identity(global_fingerprint, &entry.record_fingerprint)
            != entry.result_fingerprint
    {
        return None;
    }
    let payload = &record.payload;
    if !exact_fields(
        payload,
        &[
            "applied_exception_keys",
            DEPENDENCIES_FIELD,
            "faults",
            "path",
            "source_fingerprint",
            "threshold_override_uses",
            "warnings",
        ],
    ) || payload.field("path")?.as_str()? != entry.path
        || payload.field("source_fingerprint")?.as_str()? != entry.source_fingerprint
    {
        return None;
    }
    decode_faults(payload.field("faults")?, &entry.path)?;
    decode_faults(payload.field("warnings")?, &entry.path)?;
    decode_exceptions(payload.field("applied_exception_keys")?, &entry.path)?;
    decode_threshold_uses(payload.field("threshold_override_uses")?)?;
    let mut seen = HashSet::new();
    let mut dependencies = Vec::new();
    for value in payload.field(DEPENDENCIES_FIELD)?.as_list()? {
        let key = decode_reference(value)?;
        let _observation = observations.get(&key)?;
        if !seen.insert(key.clone()) {
            return None;
        }
        dependencies.push(key);
    }
    Some(dependencies)
}
pub(crate) fn observation_map(
    observations: &[NativeDependencyObservation],
) -> Option<HashMap<NativeDependencyKey, NativeDependencyObservation>> {
    let mut indexed = HashMap::new();
    for observation in observations {
        if let Some(existing) = indexed.insert(observation.key.clone(), observation.clone()) {
            if existing.dependency_path != observation.dependency_path
                || existing.answer != observation.answer
            {
                return None;
            }
        }
    }
    Some(indexed)
}

pub(crate) fn resolved_file_payload(
    payload: &CanonicalValue,
    owner: &str,
    dependency_keys: &[NativeDependencyKey],
    observations: &HashMap<NativeDependencyKey, NativeDependencyObservation>,
) -> Option<CanonicalValue> {
    let mut entries = payload.as_object()?.to_vec();
    let dependencies = dependency_keys
        .iter()
        .map(|key| observation_value(observations.get(key)?, owner))
        .collect::<Option<Vec<_>>>()?;
    let (_, value) = entries
        .iter_mut()
        .find(|(name, _)| name == DEPENDENCIES_FIELD)?;
    *value = CanonicalValue::List(dependencies);
    Some(CanonicalValue::Object(entries))
}

pub(crate) fn prepare_publication_candidate(
    payload: &CanonicalValue,
) -> Option<NativePublicationCandidate> {
    if !exact_fields(
        payload,
        &[
            "applied_exception_keys",
            DEPENDENCIES_FIELD,
            "faults",
            "path",
            "source_fingerprint",
            "threshold_override_uses",
            "warnings",
        ],
    ) {
        return None;
    }
    let path = payload.field("path")?.as_str()?.to_owned();
    let source_fingerprint = payload.field("source_fingerprint")?.as_str()?.to_owned();
    if !valid_relative_path(&path, false) || !valid_fingerprint(&source_fingerprint) {
        return None;
    }
    decode_faults(payload.field("faults")?, &path)?;
    decode_faults(payload.field("warnings")?, &path)?;
    decode_exceptions(payload.field("applied_exception_keys")?, &path)?;
    decode_threshold_uses(payload.field("threshold_override_uses")?)?;
    let observations = payload
        .field(DEPENDENCIES_FIELD)?
        .as_list()?
        .iter()
        .map(decode_observation)
        .collect::<Option<Vec<_>>>()?;
    if observations
        .iter()
        .any(|observation| observation.requester_path != path)
    {
        return None;
    }
    let mut seen = HashSet::new();
    if observations
        .iter()
        .any(|observation| !seen.insert(observation.key.clone()))
    {
        return None;
    }
    let references = observations
        .iter()
        .map(|observation| dependency_reference_value(&observation.key))
        .collect();
    let mut stored_entries = payload.as_object()?.to_vec();
    let (_, dependencies) = stored_entries
        .iter_mut()
        .find(|(name, _)| name == DEPENDENCIES_FIELD)?;
    *dependencies = CanonicalValue::List(references);
    Some(NativePublicationCandidate {
        path,
        source_fingerprint,
        payload: CanonicalValue::Object(stored_entries),
        contribution: collection_contribution(payload),
        observations,
    })
}

pub(crate) fn observation_value(
    observation: &NativeDependencyObservation,
    requester_path: &str,
) -> Option<CanonicalValue> {
    Some(CanonicalValue::Object(vec![
        ("answer".to_owned(), observation.answer.clone()),
        (
            "dependency_path".to_owned(),
            CanonicalValue::String(observation.dependency_path.clone()),
        ),
        (
            "kind".to_owned(),
            CanonicalValue::String(observation.key.kind.clone()),
        ),
        (
            "pattern".to_owned(),
            optional_value(&observation.key.pattern),
        ),
        (
            "query_path".to_owned(),
            CanonicalValue::String(observation.key.query_path.clone()),
        ),
        (
            "recursive".to_owned(),
            CanonicalValue::Bool(observation.key.recursive),
        ),
        (
            "requester_path".to_owned(),
            CanonicalValue::String(requester_path.to_owned()),
        ),
    ]))
}

pub(crate) fn file_result_identity(global_fingerprint: &str, record_fingerprint: &str) -> String {
    let mut digest = Sha256::new();
    digest.update(FILE_RESULT_DOMAIN);
    digest.update(global_fingerprint.as_bytes());
    digest.update(record_fingerprint.as_bytes());
    format!("{:x}", digest.finalize())
}

fn decode_index_entry(value: &CanonicalValue) -> Option<NativeIndexEntry> {
    if !exact_fields(
        value,
        &[
            "path",
            "record_fingerprint",
            "result_fingerprint",
            "source_fingerprint",
        ],
    ) {
        return None;
    }
    let entry = NativeIndexEntry {
        path: value.field("path")?.as_str()?.to_owned(),
        source_fingerprint: value.field("source_fingerprint")?.as_str()?.to_owned(),
        result_fingerprint: value.field("result_fingerprint")?.as_str()?.to_owned(),
        record_fingerprint: value.field("record_fingerprint")?.as_str()?.to_owned(),
    };
    (valid_relative_path(&entry.path, false)
        && valid_fingerprint(&entry.source_fingerprint)
        && valid_fingerprint(&entry.result_fingerprint)
        && valid_fingerprint(&entry.record_fingerprint))
    .then_some(entry)
}

fn decode_observation(value: &CanonicalValue) -> Option<NativeDependencyObservation> {
    if !exact_fields(
        value,
        &[
            "answer",
            "dependency_path",
            "kind",
            "pattern",
            "query_path",
            "recursive",
            "requester_path",
        ],
    ) {
        return None;
    }
    let observation = NativeDependencyObservation {
        requester_path: value.field("requester_path")?.as_str()?.to_owned(),
        key: NativeDependencyKey {
            query_path: value.field("query_path")?.as_str()?.to_owned(),
            kind: value.field("kind")?.as_str()?.to_owned(),
            pattern: optional_string(value.field("pattern")?)?,
            recursive: value.field("recursive")?.as_bool()?,
        },
        dependency_path: value.field("dependency_path")?.as_str()?.to_owned(),
        answer: value.field("answer")?.clone(),
    };
    (valid_relative_path(&observation.requester_path, false)
        && valid_relative_path(&observation.key.query_path, true)
        && valid_relative_path(&observation.dependency_path, true)
        && valid_dependency_shape(&observation))
    .then_some(observation)
}

fn decode_reference(value: &CanonicalValue) -> Option<NativeDependencyKey> {
    if !exact_fields(value, &["kind", "pattern", "query_path", "recursive"]) {
        return None;
    }
    let key = NativeDependencyKey {
        query_path: value.field("query_path")?.as_str()?.to_owned(),
        kind: value.field("kind")?.as_str()?.to_owned(),
        pattern: optional_string(value.field("pattern")?)?,
        recursive: value.field("recursive")?.as_bool()?,
    };
    valid_dependency_shape(&NativeDependencyObservation {
        requester_path: "owner".to_owned(),
        key: key.clone(),
        dependency_path: "dependency".to_owned(),
        answer: reference_answer(&key),
    })
    .then_some(key)
}

fn reference_answer(key: &NativeDependencyKey) -> CanonicalValue {
    match key.kind.as_str() {
        "source" => CanonicalValue::Null,
        "exists" | "is_file" | "is_dir" => CanonicalValue::Bool(false),
        _ => CanonicalValue::List(Vec::new()),
    }
}

fn dependency_reference_value(key: &NativeDependencyKey) -> CanonicalValue {
    CanonicalValue::Object(vec![
        ("kind".to_owned(), CanonicalValue::String(key.kind.clone())),
        ("pattern".to_owned(), optional_value(&key.pattern)),
        (
            "query_path".to_owned(),
            CanonicalValue::String(key.query_path.clone()),
        ),
        ("recursive".to_owned(), CanonicalValue::Bool(key.recursive)),
    ])
}

fn collection_contribution(payload: &CanonicalValue) -> Option<CanonicalValue> {
    let faults = payload.field("faults")?.as_list()?;
    let warnings = payload.field("warnings")?.as_list()?;
    let exceptions = payload.field("applied_exception_keys")?.as_list()?;
    let uses = payload.field("threshold_override_uses")?.as_list()?;
    if faults.is_empty() && warnings.is_empty() && exceptions.is_empty() && uses.is_empty() {
        return None;
    }
    Some(CanonicalValue::Object(vec![
        (
            "applied_exception_keys".to_owned(),
            payload.field("applied_exception_keys")?.clone(),
        ),
        ("faults".to_owned(), payload.field("faults")?.clone()),
        ("path".to_owned(), payload.field("path")?.clone()),
        (
            "threshold_override_uses".to_owned(),
            payload.field("threshold_override_uses")?.clone(),
        ),
        ("warnings".to_owned(), payload.field("warnings")?.clone()),
    ]))
}

fn optional_value(value: &Option<String>) -> CanonicalValue {
    value.as_ref().map_or(CanonicalValue::Null, |value| {
        CanonicalValue::String(value.clone())
    })
}
