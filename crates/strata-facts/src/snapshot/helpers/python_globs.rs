//! Ordered Python path matching helpers.

use std::fs;
use std::path::{Path, PathBuf};

pub(crate) fn python_paths(root: &Path, recursive: bool) -> Vec<PathBuf> {
    let directories = if recursive {
        directory_paths(root)
    } else {
        vec![root.to_path_buf()]
    };
    let mut paths: Vec<PathBuf> = Vec::new();
    for directory in directories {
        let entries = match fs::read_dir(directory) {
            Ok(entries) => entries,
            Err(_) => continue,
        };
        paths.extend(
            entries
                .flatten()
                .filter(|entry| entry.file_name().to_string_lossy().ends_with(".py"))
                .map(|entry| entry.path()),
        );
    }
    paths
}

pub(crate) fn python_anchor(root: &Path) -> Option<PathBuf> {
    let init_path = root.join("__init__.py");
    if init_path.is_file() {
        return Some(init_path);
    }
    let mut direct_modules = python_paths(root, false);
    direct_modules.sort();
    if let Some(path) = direct_modules.into_iter().next() {
        return Some(path);
    }
    let mut descendant_modules = python_paths(root, true);
    descendant_modules.sort();
    descendant_modules.into_iter().next()
}

fn directory_paths(root: &Path) -> Vec<PathBuf> {
    let entries: Vec<fs::DirEntry> = match fs::read_dir(root) {
        Ok(entries) => entries.flatten().collect(),
        Err(_) => return vec![root.to_path_buf()],
    };
    let directories: Vec<PathBuf> = entries
        .iter()
        .filter(|entry| entry.file_type().is_ok_and(|file_type| file_type.is_dir()))
        .map(fs::DirEntry::path)
        .collect();
    let mut paths: Vec<PathBuf> = vec![root.to_path_buf()];
    paths.extend(directories.iter().cloned());
    for directory in directories {
        let descendants = directory_paths(&directory);
        paths.extend(descendants.into_iter().skip(1));
    }
    paths
}
