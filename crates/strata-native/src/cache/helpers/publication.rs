//! Native preparation, merging, and transactional generation publication.

use std::collections::{HashMap, HashSet};
use std::path::Path;

use crate::cache::helpers::publication_merge::{
    current_index, index_payload, matching_dependencies, merged_contributions, merged_observations,
    retained_dependency_keys,
};
use crate::cache::helpers::records::{content_fingerprint, encode_canonical_record};
use crate::cache::helpers::schema::{
    file_result_identity, observation_value, prepare_publication_candidate,
};
use crate::cache::helpers::storage::mutate_records;
use crate::cache::models::{
    CacheMetrics, CacheMutation, CanonicalValue, DecodedRecord, EncodedWrite,
    NativeDependencyObservation, NativeIndexEntry, NativePublicationPreparation,
    NativePublicationResult,
};

const METADATA_PATH: &str = "metadata.json";
const INDEX_PATH: &str = "index.json";
const DEPENDENCIES_PATH: &str = "dependencies.json";
const COLLECTION_PATH: &str = "collection.json";
const METADATA_KIND: &str = "metadata";
const INDEX_KIND: &str = "index";
const DEPENDENCIES_KIND: &str = "dependencies";
const COLLECTION_KIND: &str = "collection";
const RESULT_KIND: &str = "file_result";

pub(crate) struct PublicationRequest {
    pub global_fingerprint: String,
    pub expected_index_fingerprint: Option<String>,
    pub retained_entries: Vec<NativeIndexEntry>,
    pub preparation: NativePublicationPreparation,
    pub retain_all_observations: bool,
    pub maximum_decoded_bytes: usize,
}

pub(crate) fn prepare_publication(values: Vec<CanonicalValue>) -> NativePublicationPreparation {
    let mut preparation = NativePublicationPreparation::default();
    for value in values {
        if value.is_null() {
            preparation.non_cacheable += 1;
            continue;
        }
        match prepare_publication_candidate(&value) {
            Some(candidate) => preparation.candidates.push(candidate),
            None => {
                preparation.non_cacheable += 1;
                preparation.internal_error = true;
            }
        }
    }
    preparation
}

pub(crate) fn publish_generation(
    repo_root: &Path,
    request: PublicationRequest,
) -> (NativePublicationResult, CacheMetrics) {
    let result_reads = request.retained_entries.iter().map(|entry| {
        (
            result_path(&entry.result_fingerprint),
            RESULT_KIND.to_owned(),
        )
    });
    let mut reads = vec![
        (METADATA_PATH.to_owned(), METADATA_KIND.to_owned()),
        (INDEX_PATH.to_owned(), INDEX_KIND.to_owned()),
    ];
    let reads_generation = !request.retained_entries.is_empty() || request.retain_all_observations;
    if reads_generation {
        reads.extend([
            (DEPENDENCIES_PATH.to_owned(), DEPENDENCIES_KIND.to_owned()),
            (COLLECTION_PATH.to_owned(), COLLECTION_KIND.to_owned()),
        ]);
    }
    reads.extend(result_reads);
    let mut conflicted = false;
    let maximum = request.maximum_decoded_bytes;
    let outcome = mutate_records(repo_root, &reads, maximum, |records| {
        let mutation = build_mutation(records, &request, reads_generation);
        if mutation.is_none() {
            conflicted = true;
            return Err(());
        }
        Ok(mutation)
    });
    let Some((mutation, metrics)) = outcome else {
        return (
            NativePublicationResult {
                non_cacheable: request.preparation.non_cacheable,
                storage_failed: true,
                internal_error: request.preparation.internal_error || conflicted,
                ..NativePublicationResult::default()
            },
            CacheMetrics::default(),
        );
    };
    let index_fingerprint = mutation.as_ref().and_then(|mutation| {
        mutation
            .writes
            .iter()
            .find(|write| write.key == INDEX_PATH)
            .map(|write| content_fingerprint(&write.data))
    });
    (
        NativePublicationResult {
            writes: request.preparation.candidates.len(),
            non_cacheable: request.preparation.non_cacheable,
            storage_failed: false,
            internal_error: request.preparation.internal_error,
            index_fingerprint,
        },
        metrics,
    )
}

pub(crate) fn store_check_output(
    repo_root: &Path,
    identity: (&str, &str),
    surface: (&[String], &str, &str, i64),
    maximum_decoded_bytes: usize,
) -> Option<CacheMetrics> {
    let (global_fingerprint, expected_index_fingerprint) = identity;
    let (targets, plain_output, color_output, exit_code) = surface;
    let payload = CanonicalValue::Object(vec![
        (
            "color_output".to_owned(),
            CanonicalValue::String(color_output.to_owned()),
        ),
        (
            "exit_code".to_owned(),
            CanonicalValue::Integer(exit_code.to_string()),
        ),
        (
            "global_fingerprint".to_owned(),
            CanonicalValue::String(global_fingerprint.to_owned()),
        ),
        (
            "index_fingerprint".to_owned(),
            CanonicalValue::String(expected_index_fingerprint.to_owned()),
        ),
        (
            "plain_output".to_owned(),
            CanonicalValue::String(plain_output.to_owned()),
        ),
        (
            "targets".to_owned(),
            CanonicalValue::List(
                targets
                    .iter()
                    .map(|target| CanonicalValue::String(target.clone()))
                    .collect(),
            ),
        ),
    ]);
    let encoded = encode_canonical_record("check_output", &payload, maximum_decoded_bytes)?;
    let reads = vec![
        (METADATA_PATH.to_owned(), METADATA_KIND.to_owned()),
        (INDEX_PATH.to_owned(), INDEX_KIND.to_owned()),
    ];
    let (mutation, metrics) =
        mutate_records(repo_root, &reads, maximum_decoded_bytes, |records| {
            let mut records = records.into_iter();
            let metadata = records.next().flatten();
            let index = records.next().flatten();
            if current_index(metadata.as_ref(), index.as_ref(), global_fingerprint).is_none()
                || index.as_ref().map(|record| record.fingerprint.as_str())
                    != Some(expected_index_fingerprint)
            {
                return Ok(None);
            }
            Ok(Some(CacheMutation {
                writes: vec![encoded_write("output.json", "check_output", encoded)],
                swept_prefix: None,
                retained_paths: Vec::new(),
                deleted_paths: Vec::new(),
            }))
        })?;
    mutation.map(|_| metrics)
}

fn build_mutation(
    mut records: Vec<Option<DecodedRecord>>,
    request: &PublicationRequest,
    reads_generation: bool,
) -> Option<CacheMutation> {
    let retained_records = records.split_off(if reads_generation { 4 } else { 2 });
    let mut records = records.into_iter();
    let metadata = records.next().flatten();
    let index_record = records.next().flatten();
    let dependencies_record = reads_generation.then(|| records.next().flatten()).flatten();
    let collection_record = reads_generation.then(|| records.next().flatten()).flatten();
    let existing = current_index(
        metadata.as_ref(),
        index_record.as_ref(),
        &request.global_fingerprint,
    );
    if request.expected_index_fingerprint.is_some()
        && (index_record
            .as_ref()
            .map(|record| record.fingerprint.as_str())
            != request.expected_index_fingerprint.as_deref()
            || existing.is_none())
    {
        return None;
    }
    let existing_entries = existing
        .as_ref()
        .map(|(entries, _, _)| {
            entries
                .iter()
                .map(|entry| (entry.path.as_str(), entry))
                .collect::<HashMap<_, _>>()
        })
        .unwrap_or_default();
    if request
        .retained_entries
        .iter()
        .any(|entry| existing_entries.get(entry.path.as_str()) != Some(&entry))
    {
        return None;
    }
    let old_observations = existing
        .as_ref()
        .and_then(|(_, fingerprint, _)| {
            matching_dependencies(dependencies_record.as_ref(), fingerprint.as_deref())
        })
        .unwrap_or_default();
    let retained_keys = if request.retain_all_observations {
        None
    } else {
        Some(retained_dependency_keys(
            &request.retained_entries,
            &retained_records,
            &request.global_fingerprint,
            &old_observations,
        )?)
    };
    let observations = merged_observations(
        &old_observations,
        retained_keys.as_ref(),
        &request.preparation,
    )?;
    let contributions = merged_contributions(
        existing.as_ref(),
        collection_record.as_ref(),
        &request.retained_entries,
        &request.preparation,
    );
    build_generation_mutation(request, existing.as_ref(), observations, contributions)
}

fn build_generation_mutation(
    request: &PublicationRequest,
    existing: Option<&(Vec<NativeIndexEntry>, Option<String>, Option<String>)>,
    observations: Vec<NativeDependencyObservation>,
    contributions: Vec<CanonicalValue>,
) -> Option<CacheMutation> {
    let mut writes = Vec::new();
    let mut entries = request.retained_entries.clone();
    let existing_result_fingerprints = existing
        .map(|(entries, _, _)| {
            entries
                .iter()
                .map(|entry| entry.result_fingerprint.as_str())
                .collect::<HashSet<_>>()
        })
        .unwrap_or_default();
    for candidate in &request.preparation.candidates {
        let encoded = encode_canonical_record(
            RESULT_KIND,
            &candidate.payload,
            request.maximum_decoded_bytes,
        )?;
        let record_fingerprint = content_fingerprint(&encoded);
        let result_fingerprint =
            file_result_identity(&request.global_fingerprint, &record_fingerprint);
        entries.push(NativeIndexEntry {
            path: candidate.path.clone(),
            source_fingerprint: candidate.source_fingerprint.clone(),
            result_fingerprint: result_fingerprint.clone(),
            record_fingerprint,
        });
        writes.push(EncodedWrite {
            key: result_path(&result_fingerprint),
            kind: RESULT_KIND.to_owned(),
            data: encoded,
            insert_only: !existing_result_fingerprints.contains(result_fingerprint.as_str()),
        });
    }
    entries.sort_by(|left, right| left.path.cmp(&right.path));
    if entries.windows(2).any(|pair| pair[0].path == pair[1].path) {
        return None;
    }
    let dependencies_payload = CanonicalValue::Object(vec![(
        "observations".to_owned(),
        CanonicalValue::List(
            observations
                .iter()
                .map(|observation| observation_value(observation, &observation.requester_path))
                .collect::<Option<Vec<_>>>()?,
        ),
    )]);
    let dependencies_encoded = encode_canonical_record(
        DEPENDENCIES_KIND,
        &dependencies_payload,
        request.maximum_decoded_bytes,
    )?;
    let dependencies_fingerprint = content_fingerprint(&dependencies_encoded);
    writes.push(encoded_write(
        DEPENDENCIES_PATH,
        DEPENDENCIES_KIND,
        dependencies_encoded,
    ));
    let collection_payload = CanonicalValue::Object(vec![(
        "contributions".to_owned(),
        CanonicalValue::List(contributions),
    )]);
    let collection_encoded = encode_canonical_record(
        COLLECTION_KIND,
        &collection_payload,
        request.maximum_decoded_bytes,
    )?;
    let collection_fingerprint = content_fingerprint(&collection_encoded);
    writes.push(encoded_write(
        COLLECTION_PATH,
        COLLECTION_KIND,
        collection_encoded,
    ));
    let index_payload = index_payload(
        &request.global_fingerprint,
        &entries,
        &dependencies_fingerprint,
        &collection_fingerprint,
    );
    let index_encoded =
        encode_canonical_record(INDEX_KIND, &index_payload, request.maximum_decoded_bytes)?;
    writes.push(encoded_write(INDEX_PATH, INDEX_KIND, index_encoded));
    let metadata_payload = CanonicalValue::Object(vec![(
        "global_fingerprint".to_owned(),
        CanonicalValue::String(request.global_fingerprint.clone()),
    )]);
    writes.push(encoded_write(
        METADATA_PATH,
        METADATA_KIND,
        encode_canonical_record(
            METADATA_KIND,
            &metadata_payload,
            request.maximum_decoded_bytes,
        )?,
    ));
    let retained_paths = entries
        .iter()
        .map(|entry| result_path(&entry.result_fingerprint))
        .collect::<Vec<_>>();
    let retained_fingerprints = entries
        .iter()
        .map(|entry| entry.result_fingerprint.as_str())
        .collect::<HashSet<_>>();
    let deleted_paths = existing
        .into_iter()
        .flat_map(|(entries, _, _)| entries)
        .filter(|entry| !retained_fingerprints.contains(entry.result_fingerprint.as_str()))
        .map(|entry| result_path(&entry.result_fingerprint))
        .collect();
    Some(CacheMutation {
        writes,
        swept_prefix: existing.is_none().then(|| "results".to_owned()),
        retained_paths,
        deleted_paths,
    })
}

fn encoded_write(path: &str, kind: &str, data: Vec<u8>) -> EncodedWrite {
    EncodedWrite {
        key: path.to_owned(),
        kind: kind.to_owned(),
        data,
        insert_only: false,
    }
}

fn result_path(fingerprint: &str) -> String {
    format!("results/{}/{}.json", &fingerprint[..2], fingerprint)
}
