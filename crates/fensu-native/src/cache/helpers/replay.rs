//! Native complete-generation validation and rendered-output replay.

use std::path::Path;

use crate::cache::helpers::generation::observations_are_current;
use crate::cache::helpers::schema::{
    decode_index, decode_observations, metadata_is_current, observation_map,
};
use crate::cache::helpers::schema_values::exact_fields;
use crate::cache::helpers::storage::read_records;
use crate::cache::models::{
    CacheMetrics, CanonicalValue, DecodedRecord, NativeIndexEntry, NativeReplay,
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
    merge_metrics(&mut metrics, &body_metrics);
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

fn merge_metrics(target: &mut CacheMetrics, source: &CacheMetrics) {
    target.reads += source.reads;
    target.bytes_read += source.bytes_read;
    target.writes += source.writes;
    target.bytes_written += source.bytes_written;
    target.scans += source.scans;
    target.deletes += source.deletes;
}

fn string_list(value: &CanonicalValue) -> Option<Vec<String>> {
    value
        .as_list()?
        .iter()
        .map(|item| item.as_str().map(str::to_owned))
        .collect()
}
