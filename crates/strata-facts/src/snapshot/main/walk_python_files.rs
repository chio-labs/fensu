//! Walk configured scope roots for Python entries with canonical identities.

use std::path::{Path, PathBuf};

use walkdir::WalkDir;

use crate::snapshot::helpers::matching::{has_python_suffix, root_relative_parts};
use crate::snapshot::models::WalkedEntry;

/// Return every Python-suffixed entry beneath each root without following directory links.
pub fn walk_python_files(roots: &[PathBuf]) -> Vec<Vec<WalkedEntry>> {
    roots.iter().map(|root| walked_root(root)).collect()
}

fn walked_root(root: &Path) -> Vec<WalkedEntry> {
    let mut entries: Vec<WalkedEntry> = Vec::new();
    let walk = WalkDir::new(root).min_depth(1).follow_links(false);
    for item in walk.into_iter().flatten() {
        if !has_python_suffix(item.file_name()) {
            continue;
        }
        let entry_path = item.into_path();
        let canonical_path = dunce::canonicalize(&entry_path).ok();
        let root_relative_parts = canonical_path
            .as_deref()
            .and_then(|canonical| root_relative_parts(canonical, root));
        entries.push(WalkedEntry {
            entry_path,
            canonical_path,
            root_relative_parts,
        });
    }
    entries
}
