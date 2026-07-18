//! Classify canonical source visibility through pure-Rust Git state.

use std::path::Path;

use gix::bstr::ByteSlice;

use crate::source::constants::GIT_IGNORE_FILE_NAME;
use crate::source::models::DiscoveryResult;
use crate::source::types::GitTracking;

pub(crate) fn classify(repository_root: &Path, result: &mut DiscoveryResult) {
    let Ok(repository) = gix::discover(repository_root) else {
        return;
    };
    let Some(worktree_root) = repository.workdir() else {
        return;
    };
    let Ok(index) = repository.index_or_empty() else {
        return;
    };
    let Ok(mut excludes) = repository.excludes(
        &index,
        None,
        gix::worktree::stack::state::ignore::Source::WorktreeThenIdMappingIfNotSkipped,
    ) else {
        return;
    };
    for document in &mut result.documents {
        document.git_tracking = classify_path(
            &repository,
            worktree_root,
            &index,
            &mut excludes,
            &document.canonical_path.filesystem_path,
        );
    }
    for file in &mut result.skill_files {
        file.git_tracking = classify_path(
            &repository,
            worktree_root,
            &index,
            &mut excludes,
            &file.canonical_path.filesystem_path,
        );
    }
}

fn classify_path(
    repository: &gix::Repository,
    worktree_root: &Path,
    index: &gix::worktree::Index,
    excludes: &mut gix::AttributeStack<'_>,
    path: &Path,
) -> GitTracking {
    let Ok(relative) = path.strip_prefix(worktree_root) else {
        return GitTracking::Unavailable;
    };
    let index_path = gix::path::to_unix_separators_on_windows(gix::path::into_bstr(relative));
    if index.entry_by_path(index_path.as_bstr()).is_some() {
        return GitTracking::Tracked;
    }
    let Ok(platform) = excludes.at_path(relative, None) else {
        return GitTracking::Unavailable;
    };
    let Some(matched) = platform.matching_exclude_pattern() else {
        return GitTracking::Untracked;
    };
    if matched.pattern.is_negative() {
        return GitTracking::Untracked;
    }
    let Some(source) = matched.source else {
        return GitTracking::Unavailable;
    };
    if source == repository.common_dir().join("info/exclude") {
        return GitTracking::IgnoredLocal;
    }
    if source.starts_with(worktree_root)
        && source
            .file_name()
            .is_some_and(|name| name == GIT_IGNORE_FILE_NAME)
    {
        return GitTracking::IgnoredRepository;
    }
    GitTracking::IgnoredGlobal
}
