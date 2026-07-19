//! Native complete-generation validation and rendered-output replay.

use std::path::Path;

use crate::cache::helpers::replay::build_replay_generation;
use crate::cache::models::{CacheMetrics, NativeReplay};

pub(crate) fn replay_generation(
    repo_root: &Path,
    global_fingerprint: &str,
    targets: &[(String, Option<String>)],
    maximum_decoded_bytes: usize,
) -> Option<(NativeReplay, CacheMetrics)> {
    build_replay_generation(
        repo_root,
        global_fingerprint,
        targets,
        maximum_decoded_bytes,
    )
}
