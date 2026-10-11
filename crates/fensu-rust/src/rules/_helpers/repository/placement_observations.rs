//! Filesystem state needed to reuse file-placement results safely.

use std::path::Path;

use crate::constants;
use crate::rules::_helpers::imports::embedded_files;
use crate::rules::_helpers::repository::package_entries;
use crate::rules::_helpers::sources::scanning;

pub(crate) fn collect(root: &Path) -> Result<Vec<String>, String> {
    let mut workspace = scanning::scan_workspace(root);
    workspace
        .violations
        .sort_by(|left, right| left.sort_key().cmp(&right.sort_key()));
    let mut observations: Vec<String> = Vec::new();
    for violation in workspace.violations {
        observations.push(format!("{violation:?}"));
    }
    for package in workspace.crates {
        observations.extend(package_observations(root, &package.directory)?);
        for file in package.files {
            observations.push(file.path.to_string_lossy().into_owned());
            observations.push(file.source.clone());
            observations.extend(embedded_files::observations(&file)?);
        }
    }
    Ok(observations)
}

fn package_observations(root: &Path, package: &Path) -> Result<Vec<String>, String> {
    let mut observations = vec![package.to_string_lossy().into_owned()];
    for entry in package_entries::entries(package)? {
        let kind = entry.file_type().map_err(|error| error.to_string())?;
        if entry.file_name() == constants::TARGET_KEY && kind.is_dir() {
            continue;
        }
        observations.push(format!("{:?}", entry.file_name()));
        observations.push(format!(
            "file={} directory={} symlink={}",
            kind.is_file(),
            kind.is_dir(),
            kind.is_symlink()
        ));
    }
    for path in package_entries::ignore_files(root, package) {
        observations.push(path.to_string_lossy().into_owned());
        match package_entries::ignore_content(&path)? {
            Some(content) => {
                observations.push("present".to_owned());
                observations.push(content);
            }
            None => observations.push("missing".to_owned()),
        }
    }
    Ok(observations)
}
