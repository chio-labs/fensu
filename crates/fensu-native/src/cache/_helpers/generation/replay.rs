//! Native complete-generation validation and rendered-output replay.

use std::collections::HashMap;
use std::path::Path;

use globset::GlobBuilder;

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
    targets: &[(String, String, Option<String>)],
    tree_snapshot: Option<&CanonicalValue>,
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
    observations_are_current(repo_root, &indexed, tree_snapshot).then_some((replay, metrics))
}

pub(crate) fn replay_dependency_kinds(
    repo_root: &Path,
    global_fingerprint: &str,
    _targets: &[(String, String, Option<String>)],
    maximum_decoded_bytes: usize,
) -> Option<(Vec<String>, CacheMetrics)> {
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
    let (_, dependencies_fingerprint, _) = decode_index(&index, global_fingerprint)?;
    let reads = vec![("dependencies.json".to_owned(), "dependencies".to_owned())];
    let (records, body_metrics) = read_records(repo_root, &reads, maximum_decoded_bytes)?;
    metrics.merge(&body_metrics);
    let dependencies = records.into_iter().next()??;
    if Some(dependencies.fingerprint.as_str()) != dependencies_fingerprint.as_deref() {
        return None;
    }
    let observations = decode_observations(&dependencies)?;
    let mut kinds = observations
        .into_iter()
        .map(|observation| observation.key.kind)
        .collect::<Vec<_>>();
    kinds.sort();
    kinds.dedup();
    Some((kinds, metrics))
}

fn current_manifest(
    entries: &[NativeIndexEntry],
    targets: &[(String, String, Option<String>)],
) -> Option<()> {
    if entries.len() != targets.len() {
        return None;
    }
    for (entry, (target_kind, target_identity, target_fingerprint)) in entries.iter().zip(targets) {
        let fingerprint = target_fingerprint.as_ref()?;
        if entry.subject_kind != *target_kind
            || entry.subject_identity != *target_identity
            || entry.source_fingerprint != *fingerprint
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
    targets: &[(String, String, Option<String>)],
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
        .map(|(_, identity, _)| identity.clone())
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
    tree_snapshot: Option<&CanonicalValue>,
) -> bool {
    let current = observe_dependencies(repo_root, observations, tree_snapshot);
    current.len() == observations.len() && current.values().all(|value| *value)
}

pub(super) fn observe_dependencies(
    repo_root: &Path,
    observations: &HashMap<NativeDependencyKey, NativeDependencyObservation>,
    tree_snapshot: Option<&CanonicalValue>,
) -> HashMap<NativeDependencyKey, bool> {
    let tree_results = observations
        .iter()
        .filter(|(key, _)| key.kind.starts_with("tree_"))
        .map(|(key, expected)| {
            let root_prefix = tree_snapshot
                .and_then(|snapshot| snapshot.field("root_prefix"))
                .and_then(CanonicalValue::as_str);
            (
                key.clone(),
                observe_tree_query(key, tree_snapshot).is_some_and(|answer| {
                    root_prefix == Some(expected.dependency_path.as_str())
                        && answer == expected.answer
                }),
            )
        })
        .collect::<HashMap<_, _>>();
    let graph_results = observations
        .iter()
        .filter(|(key, _)| key.kind.starts_with("graph_"))
        .map(|(key, expected)| {
            let root_prefix = tree_snapshot
                .and_then(|snapshot| snapshot.field("graph"))
                .and_then(|graph| graph.field("root_prefix"))
                .and_then(CanonicalValue::as_str);
            (
                key.clone(),
                observe_graph_query(key, tree_snapshot).is_some_and(|answer| {
                    root_prefix == Some(expected.dependency_path.as_str())
                        && answer == expected.answer
                }),
            )
        })
        .collect::<HashMap<_, _>>();
    let queries = observations
        .keys()
        .filter(|key| !key.kind.starts_with("tree_") && !key.kind.starts_with("graph_"))
        .map(|key| RepositoryObservationQuery {
            relative_path: key.query_path.clone(),
            kind: key.kind.clone(),
            pattern: key.pattern.clone(),
            recursive: key.recursive,
        })
        .collect::<Vec<_>>();
    let Some(index) = build_repository_observation_index(repo_root, &queries) else {
        let mut results = tree_results;
        results.extend(graph_results);
        return results;
    };
    let mut results = queries
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
        .collect::<HashMap<_, _>>();
    results.extend(tree_results);
    results.extend(graph_results);
    results
}

fn observe_tree_query(
    key: &NativeDependencyKey,
    snapshot: Option<&CanonicalValue>,
) -> Option<CanonicalValue> {
    let snapshot = snapshot?;
    let root_prefix = snapshot.field("root_prefix")?.as_str()?;
    let paths = string_values(snapshot.field("paths")?)?;
    let files = string_values(snapshot.field("files")?)?;
    let answer = match key.kind.as_str() {
        "tree_paths" => paths,
        "tree_files" => files,
        "tree_children" => paths
            .into_iter()
            .filter(|path| parent_path(path) == key.query_path)
            .collect(),
        "tree_descendants" => paths
            .into_iter()
            .filter(|path| is_under(path, &key.query_path) && path != &key.query_path)
            .collect(),
        "tree_files_under" => files
            .into_iter()
            .filter(|path| path == &key.query_path || is_under(path, &key.query_path))
            .collect(),
        "tree_glob" => {
            let pattern = key.pattern.as_ref()?;
            paths
                .into_iter()
                .filter(|path| {
                    project_relative_path(path, root_prefix)
                        .is_some_and(|relative| python_path_matches(relative, pattern))
                })
                .collect()
        }
        "tree_position" => {
            return snapshot
                .field("positions")?
                .field(&key.query_path)
                .cloned()
                .or(Some(CanonicalValue::String("null".to_owned())));
        }
        _ => return None,
    };
    Some(CanonicalValue::List(
        answer.into_iter().map(CanonicalValue::String).collect(),
    ))
}

fn observe_graph_query(
    key: &NativeDependencyKey,
    snapshot: Option<&CanonicalValue>,
) -> Option<CanonicalValue> {
    let graph = snapshot?.field("graph")?;
    let root_prefix = graph.field("root_prefix")?.as_str()?;
    match key.kind.as_str() {
        "graph_nodes" if key.query_path == root_prefix => graph.field("nodes").cloned(),
        "graph_node" => graph
            .field("node")?
            .field(&key.query_path)
            .cloned()
            .or(Some(CanonicalValue::String("null".to_owned()))),
        "graph_dependencies" => graph.field("dependencies")?.field(&key.query_path).cloned(),
        "graph_dependents" => graph.field("dependents")?.field(&key.query_path).cloned(),
        "graph_imports" => graph.field("imports")?.field(&key.query_path).cloned(),
        "graph_cycles" if key.query_path == root_prefix => graph.field("cycles").cloned(),
        _ => None,
    }
}

fn project_relative_path<'a>(path: &'a str, root_prefix: &str) -> Option<&'a str> {
    if root_prefix == "." {
        return Some(path);
    }
    path.strip_prefix(root_prefix)?.strip_prefix('/')
}

fn python_path_matches(path: &str, pattern: &str) -> bool {
    if !pattern.contains('/') {
        return build_glob(pattern).is_some_and(|matcher| {
            matcher.is_match(path.rsplit_once('/').map_or(path, |(_, name)| name))
        });
    }
    let suffixes =
        std::iter::once(path).chain(path.match_indices('/').map(|(index, _)| &path[index + 1..]));
    build_glob(pattern).is_some_and(|matcher| {
        suffixes
            .clone()
            .any(|candidate| matcher.is_match(candidate))
    })
}

fn build_glob(pattern: &str) -> Option<globset::GlobMatcher> {
    let normalized = pattern
        .split('/')
        .map(|part| if part == "**" { "*" } else { part })
        .collect::<Vec<_>>()
        .join("/");
    Some(
        GlobBuilder::new(&normalized)
            .literal_separator(true)
            .build()
            .ok()?
            .compile_matcher(),
    )
}

fn string_values(value: &CanonicalValue) -> Option<Vec<String>> {
    value
        .as_list()?
        .iter()
        .map(|item| item.as_str().map(str::to_owned))
        .collect()
}

fn parent_path(path: &str) -> &str {
    path.rsplit_once('/').map_or(".", |(parent, _)| parent)
}

fn is_under(path: &str, parent: &str) -> bool {
    parent == "."
        || path
            .strip_prefix(parent)
            .is_some_and(|suffix| suffix.starts_with('/'))
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

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn graph_dependency_observation_matches_snapshot_answer() {
        let key = NativeDependencyKey {
            query_path: "src/example/entry.py".to_owned(),
            kind: "graph_dependencies".to_owned(),
            pattern: None,
            recursive: false,
        };
        let answer = CanonicalValue::String("[]".to_owned());
        let snapshot = CanonicalValue::Object(vec![(
            "graph".to_owned(),
            CanonicalValue::Object(vec![
                (
                    "root_prefix".to_owned(),
                    CanonicalValue::String(".".to_owned()),
                ),
                (
                    "dependencies".to_owned(),
                    CanonicalValue::Object(vec![(key.query_path.clone(), answer.clone())]),
                ),
            ]),
        )]);
        let observations = HashMap::from([(
            key.clone(),
            NativeDependencyObservation {
                requester_path: ".fensu-project-rule".to_owned(),
                key: key.clone(),
                dependency_path: ".".to_owned(),
                answer,
            },
        )]);

        assert_eq!(
            observe_dependencies(Path::new("."), &observations, Some(&snapshot)),
            HashMap::from([(key, true)])
        );
    }

    #[test]
    fn nested_graph_cycle_observation_uses_explicit_root_prefix() {
        let key = NativeDependencyKey {
            query_path: "workspace".to_owned(),
            kind: "graph_cycles".to_owned(),
            pattern: None,
            recursive: false,
        };
        let answer = CanonicalValue::String("[]".to_owned());
        let snapshot = CanonicalValue::Object(vec![(
            "graph".to_owned(),
            CanonicalValue::Object(vec![
                (
                    "root_prefix".to_owned(),
                    CanonicalValue::String("workspace".to_owned()),
                ),
                ("cycles".to_owned(), answer.clone()),
            ]),
        )]);
        let observations = HashMap::from([(
            key.clone(),
            NativeDependencyObservation {
                requester_path: ".fensu-project-rule".to_owned(),
                key: key.clone(),
                dependency_path: "workspace".to_owned(),
                answer,
            },
        )]);

        assert_eq!(
            observe_dependencies(Path::new("."), &observations, Some(&snapshot)),
            HashMap::from([(key, true)])
        );
    }

    #[test]
    fn tree_glob_matching_preserves_pure_path_double_star_segments() {
        assert!(!python_path_matches("entry.py", "**/*.py"));
        assert!(python_path_matches("src/entry.py", "**/*.py"));
        assert!(!python_path_matches("src/entry.py", "src/**/*.py"));
        assert!(python_path_matches("src/orders/entry.py", "src/**/*.py"));
        assert!(!python_path_matches(
            "src/orders/main/entry.py",
            "src/**/*.py"
        ));
    }
}
