//! Walk configured scope roots for Python entries with canonical identities.

use std::path::{Path, PathBuf};

use walkdir::WalkDir;

use crate::snapshot::_helpers::matching::{has_python_suffix, root_relative_parts};
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
        let (canonical_path, root_relative_parts) = match dunce::canonicalize(&entry_path) {
            Ok(canonical_path) => {
                let relative_parts = root_relative_parts(&canonical_path, root);
                (Some(canonical_path), relative_parts)
            }
            Err(_) => (None, None),
        };
        entries.push(WalkedEntry {
            entry_path,
            canonical_path,
            root_relative_parts,
        });
    }
    entries
}
