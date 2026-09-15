//! Native complete-generation validation and rendered-output replay.

use std::path::Path;

use crate::cache::_helpers::replay::{build_replay_generation, replay_dependency_kinds};
use crate::cache::models::{CacheMetrics, CanonicalValue, NativeReplay};

pub(in crate::cache) fn replay_generation(
    repo_root: &Path,
    global_fingerprint: &str,
    targets: &[(String, String, Option<String>)],
    tree_snapshot: Option<&CanonicalValue>,
    maximum_decoded_bytes: usize,
) -> Option<(NativeReplay, CacheMetrics)> {
    build_replay_generation(
        repo_root,
        global_fingerprint,
        targets,
        tree_snapshot,
        maximum_decoded_bytes,
    )
}

pub(in crate::cache) fn dependency_kinds(
    repo_root: &Path,
    global_fingerprint: &str,
    targets: &[(String, String, Option<String>)],
    maximum_decoded_bytes: usize,
) -> Option<(Vec<String>, CacheMetrics)> {
    replay_dependency_kinds(
        repo_root,
        global_fingerprint,
        targets,
        maximum_decoded_bytes,
    )
}
