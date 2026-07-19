//! Check every workspace crate and return sorted structure violations.

use std::path;

use crate::constants;
use crate::models;
use crate::rules::helpers::containers;
use crate::rules::helpers::layers;
use crate::rules::helpers::scanning;
use crate::rules::helpers::tests_layout;

/// Check the workspace under repo_root and return deterministic violations.
pub fn check_repository(repo_root: &path::Path) -> Vec<models::Violation> {
    let workspace = scanning::scan_workspace(repo_root);
    let mut violations = workspace.violations;
    for crate_dir in workspace.crate_directories {
        violations.extend(check_crate(repo_root, &crate_dir));
    }
    violations.sort_by(|left, right| left.sort_key().cmp(&right.sort_key()));
    violations
}

fn check_crate(repo_root: &path::Path, crate_dir: &path::Path) -> Vec<models::Violation> {
    let mut violations: Vec<models::Violation> = Vec::new();
    let src_root = crate_dir.join(constants::SOURCE_DIRECTORY);
    let tests_root = crate_dir.join(constants::TESTS_DIRECTORY);
    let src_scan = scanning::rust_files(repo_root, &src_root);
    let test_scan = scanning::rust_files(repo_root, &tests_root);
    violations.extend(src_scan.violations);
    violations.extend(test_scan.violations);
    for file in &src_scan.files {
        violations.extend(scanning::check_source_file(repo_root, &src_root, file));
    }
    for file in &test_scan.files {
        violations.extend(scanning::check_test_file(repo_root, &tests_root, file));
    }
    violations.extend(containers::check_containers(&src_scan.files));
    violations.extend(tests_layout::check_test_mirroring(repo_root, crate_dir));
    violations.extend(layers::check_manifest(repo_root, crate_dir));
    violations
}
