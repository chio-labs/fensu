//! Temporary-tree helpers for snapshot tests.

use std::fs;
use std::path::{Path, PathBuf};
use std::sync::atomic;

use strata_facts::snapshot::models::{RepositoryObservationQuery, RepositoryObservationState};

use crate::test_types;

static TREE_COUNTER: atomic::AtomicUsize = atomic::AtomicUsize::new(0);

pub(crate) fn write_temp_tree(
    files: &[test_types::FixtureFile],
    symlinks: &[test_types::FixtureSymlink],
) -> PathBuf {
    let index = TREE_COUNTER.fetch_add(1, atomic::Ordering::SeqCst);
    let base = std::env::temp_dir().join(format!(
        "strata-facts-snapshot-{}-{index}",
        std::process::id()
    ));
    fs::create_dir_all(&base).expect("temporary tree base is writable");
    for file in files {
        let file_path = base.join(file.path);
        let parent = file_path.parent().expect("fixture paths name a parent");
        fs::create_dir_all(parent).expect("fixture directories are writable");
        fs::write(&file_path, file.contents).expect("fixture files are writable");
    }
    for symlink in symlinks {
        let link_path = base.join(symlink.path);
        let parent = link_path.parent().expect("symlink paths name a parent");
        fs::create_dir_all(parent).expect("symlink directories are writable");
        std::os::unix::fs::symlink(base.join(symlink.target), &link_path)
            .expect("fixture symlinks are creatable");
    }
    fs::canonicalize(&base).expect("temporary tree base canonicalizes")
}

pub(crate) fn remove_temp_tree(base: &Path) {
    fs::remove_dir_all(base).expect("temporary tree base is removable");
}

pub(crate) fn expected_rows(
    entries: &[test_types::ExpectedEntry],
) -> Vec<(String, Option<Vec<String>>)> {
    entries
        .iter()
        .map(|entry| {
            let parts = entry
                .expected_parts
                .map(|parts| parts.iter().map(|part| (*part).to_owned()).collect());
            (entry.entry_suffix.to_owned(), parts)
        })
        .collect()
}

pub(crate) fn observation_query(
    path: &str,
    kind: &str,
    pattern: Option<&str>,
    recursive: bool,
) -> RepositoryObservationQuery {
    RepositoryObservationQuery {
        relative_path: path.to_owned(),
        kind: kind.to_owned(),
        pattern: pattern.map(str::to_owned),
        recursive,
    }
}

pub(crate) fn observation_paths(answer: &RepositoryObservationState) -> Vec<String> {
    answer
        .answer
        .as_paths()
        .expect("expected path answer")
        .to_vec()
}

pub(crate) fn owned_strings(values: &[&str]) -> Vec<String> {
    values.iter().map(ToString::to_string).collect()
}
