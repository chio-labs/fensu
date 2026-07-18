//! Native complete-generation validation and rendered-output replay.

use std::path::{Path, PathBuf};

use strata_facts::snapshot::main::observe_python_globs::observe_python_globs;
use strata_facts::snapshot::main::observe_repository_contexts::observe_repository_contexts;
use strata_facts::snapshot::main::observe_repository_stats::observe_repository_stats;
use strata_facts::snapshot::models::{
    RepositoryContextKind, RepositoryContextQuery, RepositoryPythonGlobQuery, RepositoryStatKind,
    RepositoryStatQuery,
};

use crate::cache::constants::PYTHON_GLOB_PATTERN;
use crate::cache::helpers::storage::read_records;
use crate::cache::models::{CacheMetrics, CanonicalValue, DecodedRecord, NativeReplay};

const REPLAY_READS: [(&str, &str); 4] = [
    ("metadata.json", "metadata"),
    ("index.json", "index"),
    ("output.json", "check_output"),
    ("dependencies.json", "dependencies"),
];

pub(crate) fn build_replay_generation(
    repo_root: &Path,
    global_fingerprint: &str,
    targets: &[(String, Option<String>)],
    maximum_decoded_bytes: usize,
) -> Option<(NativeReplay, CacheMetrics)> {
    let reads = REPLAY_READS
        .iter()
        .map(|(path, kind)| ((*path).to_owned(), (*kind).to_owned()))
        .collect::<Vec<_>>();
    let (records, metrics) = read_records(repo_root, &reads, maximum_decoded_bytes)?;
    let mut records = records.into_iter();
    let metadata = records.next()??;
    let index = records.next()??;
    let output = records.next()??;
    let dependencies = records.next()??;
    if metadata.payload.field("global_fingerprint")?.as_str()? != global_fingerprint
        || index.payload.field("global_fingerprint")?.as_str()? != global_fingerprint
    {
        return None;
    }
    current_manifest(&index.payload, targets)?;
    let dependencies_fingerprint = index.payload.field("dependencies_fingerprint")?.as_str()?;
    if dependencies.fingerprint != dependencies_fingerprint {
        return None;
    }
    let replay = current_output(&output, global_fingerprint, &index.fingerprint, targets)?;
    let observations = dependencies.payload.field("observations")?.as_list()?;
    observations_are_current(repo_root, observations).then_some((replay, metrics))
}

fn current_manifest(index: &CanonicalValue, targets: &[(String, Option<String>)]) -> Option<()> {
    let entries = index.field("entries")?.as_list()?;
    if entries.len() != targets.len() {
        return None;
    }
    for (entry, (target_path, target_fingerprint)) in entries.iter().zip(targets) {
        let fingerprint = target_fingerprint.as_ref()?;
        if entry.field("path")?.as_str()? != target_path
            || entry.field("source_fingerprint")?.as_str()? != fingerprint
        {
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
    if payload.field("global_fingerprint")?.as_str()? != global_fingerprint
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

fn observations_are_current(repo_root: &Path, observations: &[CanonicalValue]) -> bool {
    observations
        .iter()
        .all(|observation| observation_is_current(repo_root, observation).unwrap_or(false))
}

fn observation_is_current(repo_root: &Path, observation: &CanonicalValue) -> Option<bool> {
    let query_path = observation.field("query_path")?.as_str()?;
    let dependency_path = observation.field("dependency_path")?.as_str()?;
    let kind = observation.field("kind")?.as_str()?;
    let recursive = observation.field("recursive")?.as_bool()?;
    let pattern = observation.field("pattern")?;
    let answer = observation.field("answer")?;
    let relative_path = PathBuf::from(query_path);
    match kind {
        "exists" | "is_file" | "is_dir" => {
            if recursive || !pattern.is_null() {
                return None;
            }
            let kind = match kind {
                "exists" => RepositoryStatKind::Exists,
                "is_file" => RepositoryStatKind::IsFile,
                _ => RepositoryStatKind::IsDir,
            };
            let observed = observe_repository_stats(
                repo_root,
                &[RepositoryStatQuery {
                    relative_path,
                    kind,
                }],
            )
            .into_iter()
            .next()??;
            Some(
                observed.dependency_path == dependency_path
                    && Some(observed.answer) == answer.as_bool(),
            )
        }
        "source" | "directory_entries" | "python_anchor" => {
            if recursive || !pattern.is_null() {
                return None;
            }
            let kind = match kind {
                "source" => RepositoryContextKind::Source,
                "directory_entries" => RepositoryContextKind::DirectoryEntries,
                _ => RepositoryContextKind::PythonAnchor,
            };
            let observed = observe_repository_contexts(
                repo_root,
                &[RepositoryContextQuery {
                    relative_path,
                    kind,
                }],
            )
            .into_iter()
            .next()??;
            if observed.dependency_path != dependency_path {
                return Some(false);
            }
            if matches!(kind, RepositoryContextKind::Source) {
                return Some(match (answer, observed.source_answer) {
                    (CanonicalValue::Null, None) => true,
                    (CanonicalValue::String(expected), Some(actual)) => expected == &actual,
                    _ => false,
                });
            }
            Some(string_list(answer)? == observed.path_answer)
        }
        "glob" => {
            if pattern.as_str()? != PYTHON_GLOB_PATTERN {
                return None;
            }
            let observed = observe_python_globs(
                repo_root,
                &[RepositoryPythonGlobQuery {
                    relative_path,
                    recursive,
                }],
            )
            .into_iter()
            .next()??;
            Some(
                observed.dependency_path == dependency_path
                    && string_list(answer)? == observed.answer,
            )
        }
        _ => None,
    }
}

fn string_list(value: &CanonicalValue) -> Option<Vec<String>> {
    value
        .as_list()?
        .iter()
        .map(|item| item.as_str().map(str::to_owned))
        .collect()
}
