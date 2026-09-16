//! Native cached-generation dependency kind discovery.

use std::path::Path;

use crate::cache::_helpers::replay::replay_dependency_kinds;
use crate::cache::models::CacheMetrics;

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
