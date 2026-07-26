//! Check every workspace crate and return sorted structure violations.

use std::path;

use crate::constants;
use crate::models;
use crate::rules::_helpers::functions::shape_project;
use crate::rules::_helpers::imports::layers;
use crate::rules::_helpers::imports::visibility;
use crate::rules::_helpers::roles::containers;
use crate::rules::_helpers::roles::domains;
use crate::rules::_helpers::roles::ownership;
use crate::rules::_helpers::roles::surfaces;
use crate::rules::_helpers::roles::tooling;
use crate::rules::_helpers::sources::scanning;
use crate::rules::_helpers::test_conventions::test_mirroring;

/// Check the workspace under repo_root and return deterministic violations.
pub fn check_repository(repo_root: &path::Path) -> Vec<models::Violation> {
    let workspace = scanning::scan_workspace(repo_root);
    let mut violations = workspace.violations;
    violations.extend(visibility::check_workspace(
        repo_root,
        &workspace.crate_directories,
    ));
    violations.extend(shape_project::check_workspace(
        repo_root,
        &workspace.crate_directories,
    ));
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
    violations.extend(domains::check_domains(&src_scan.files));
    violations.extend(ownership::check(crate_dir, &src_scan.files));
    violations.extend(surfaces::check(&src_scan.files));
    if crate_dir
        .file_name()
        .is_some_and(|name| name == constants::TOOLING_CRATE_NAME)
    {
        violations.extend(tooling::check(&src_scan.files));
    }
    violations.extend(test_mirroring::check_test_mirroring(repo_root, crate_dir));
    violations.extend(test_mirroring::check_harness_coverage(repo_root, crate_dir));
    violations.extend(layers::check_manifest(repo_root, crate_dir));
    violations
}
