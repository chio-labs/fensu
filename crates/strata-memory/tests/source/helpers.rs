//! Temporary repository helpers for canonical source tests.

use std::fs;
use std::path::{Path, PathBuf};
use std::sync::atomic::{AtomicUsize, Ordering};

use strata_memory::source::models::DiscoveryResult;
use strata_memory::source::types::DiagnosticKind;

use crate::test_types::{FixtureDirectory, FixtureFile, FixtureSymlink};

static TREE_COUNTER: AtomicUsize = AtomicUsize::new(0);

pub(crate) fn write_temp_tree(directories: &[FixtureDirectory], files: &[FixtureFile]) -> PathBuf {
    let index = TREE_COUNTER.fetch_add(1, Ordering::SeqCst);
    let root = std::env::temp_dir().join(format!(
        "strata-memory-source-{}-{index}",
        std::process::id()
    ));
    let _ = fs::remove_dir_all(&root);
    fs::create_dir_all(&root).expect("temporary repository root is writable");
    for directory in directories {
        fs::create_dir_all(root.join(directory.path)).expect("fixture directory is writable");
    }
    for file in files {
        let path = root.join(file.path);
        fs::create_dir_all(path.parent().expect("fixture file has a parent"))
            .expect("fixture parent is writable");
        fs::write(path, file.contents).expect("fixture file is writable");
    }
    root
}

#[cfg(unix)]
pub(crate) fn write_symlinks(root: &Path, symlinks: &[FixtureSymlink]) {
    for symlink in symlinks {
        let path = root.join(symlink.path);
        fs::create_dir_all(path.parent().expect("symlink fixture has a parent"))
            .expect("symlink parent is writable");
        std::os::unix::fs::symlink(root.join(symlink.target), path)
            .expect("fixture symlink is creatable");
    }
}

pub(crate) fn document_paths(result: &DiscoveryResult) -> Vec<&str> {
    result
        .documents
        .iter()
        .map(|document| document.canonical_path.repository_relative.as_str())
        .collect()
}

pub(crate) fn skill_file_paths(result: &DiscoveryResult) -> Vec<&str> {
    result
        .skill_files
        .iter()
        .map(|file| file.canonical_path.repository_relative.as_str())
        .collect()
}

pub(crate) fn diagnostic_rows(result: &DiscoveryResult) -> Vec<(&str, DiagnosticKind)> {
    result
        .diagnostics
        .iter()
        .map(|diagnostic| {
            (
                diagnostic.repository_relative_path.as_str(),
                diagnostic.kind,
            )
        })
        .collect()
}

pub(crate) fn remove_temp_tree(root: &Path) {
    fs::remove_dir_all(root).expect("temporary repository is removable");
}
