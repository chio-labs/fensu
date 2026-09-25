//! Locate the configuration owner of a target-local project root.

use std::path::{Component, Path, PathBuf};

pub(crate) fn configuration_directory(project_root: &Path, target_root: &str) -> PathBuf {
    let mut directory = project_root.to_path_buf();
    for component in Path::new(target_root).components() {
        if matches!(component, Component::Normal(_)) {
            directory.pop();
        }
    }
    directory
}
