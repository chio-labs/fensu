//! Role-surface rules that require the complete crate source tree.

use std::collections::BTreeSet;
use std::path;

use crate::constants;
use crate::models;

pub(crate) fn check(files: &[models::SourceFile]) -> Vec<models::Violation> {
    let paths: BTreeSet<&str> = files.iter().map(|file| file.relative.as_str()).collect();
    files
        .iter()
        .filter(|file| file.has_directory(constants::MAIN_DIRECTORY))
        .filter(|file| file.file_name() != constants::MOD_FILE)
        .filter(|file| file.relative.ends_with(".rs"))
        .filter(|file| collides_with_bucket(file, &paths))
        .map(|file| {
            models::Violation::new(models::ViolationRequest {
                code: "RSR405",
                path: path::Path::new(&file.relative),
                line: None,
                message: "main entry name collides with a same-named module directory",
                remediation: "keep either the flat entry module or the same-named module directory",
            })
        })
        .collect()
}

fn collides_with_bucket(file: &models::SourceFile, paths: &BTreeSet<&str>) -> bool {
    let package_prefix = file.relative.trim_end_matches(".rs");
    paths
        .iter()
        .any(|candidate| candidate.starts_with(&format!("{package_prefix}/")))
}
