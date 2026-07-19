//! Discovery phase orchestration and deterministic result ordering.

use std::path::Path;

use crate::source::helpers::{collisions, git_tracking, tree};
use crate::source::models::DiscoveryResult;

pub(crate) fn collect_memory_sources(repository_root: &Path) -> DiscoveryResult {
    let mut result = tree::walk_repository(repository_root);
    git_tracking::classify(repository_root, &mut result);
    collisions::append_collision_diagnostics(repository_root, &mut result);
    result.documents.sort_by(|left, right| {
        left.canonical_path
            .repository_relative
            .cmp(&right.canonical_path.repository_relative)
    });
    result.skill_files.sort_by(|left, right| {
        left.canonical_path
            .repository_relative
            .cmp(&right.canonical_path.repository_relative)
    });
    result.diagnostics.sort_by(|left, right| {
        (&left.repository_relative_path, left.kind, &left.message).cmp(&(
            &right.repository_relative_path,
            right.kind,
            &right.message,
        ))
    });
    result
}
