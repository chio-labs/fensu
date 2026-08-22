//! Check every workspace crate under explicit consumer configuration.

use std::path;

use crate::constants;
use crate::models;
use crate::rules::_helpers::functions::shape_project;
use crate::rules::_helpers::imports::{layers, visibility};
use crate::rules::_helpers::roles::{containers, domains, ownership, surfaces, tooling};
use crate::rules::_helpers::sources::scanning;
use crate::rules::_helpers::test_conventions::test_mirroring;

/// Check a workspace using explicit consumer identities and boundaries.
pub fn check_repository_with_config(
    repo_root: &path::Path,
    config: &models::CheckerConfig,
) -> Result<Vec<models::Violation>, String> {
    config.validate()?;
    let workspace = scanning::scan_workspace(repo_root);
    let mut violations = workspace.violations;
    let crate_directories = workspace
        .crates
        .iter()
        .map(|workspace_crate| workspace_crate.directory.clone())
        .collect::<Vec<_>>();
    violations.extend(visibility::check_workspace(repo_root, &crate_directories));
    violations.extend(shape_project::check_workspace(
        repo_root,
        &crate_directories,
    ));
    for workspace_crate in workspace.crates {
        violations.extend(check_crate(repo_root, &workspace_crate, config));
    }
    violations.sort_by(|left, right| left.sort_key().cmp(&right.sort_key()));
    Ok(violations)
}

fn check_crate(
    repo_root: &path::Path,
    workspace_crate: &models::WorkspaceCrate,
    config: &models::CheckerConfig,
) -> Vec<models::Violation> {
    let crate_dir = &workspace_crate.directory;
    let is_tooling_crate = workspace_crate.package_name.as_deref() == Some(&config.tooling.package);
    let mut violations: Vec<models::Violation> = Vec::new();
    let src_root = crate_dir.join(constants::SOURCE_DIRECTORY);
    let tests_root = crate_dir.join(constants::TESTS_DIRECTORY);
    let src_scan = scanning::rust_files(repo_root, &src_root);
    let test_scan = scanning::rust_files(repo_root, &tests_root);
    violations.extend(src_scan.violations);
    violations.extend(test_scan.violations);
    for file in &src_scan.files {
        violations.extend(scanning::check_source_file(models::SourceCheckRequest {
            repo_root,
            src_root: &src_root,
            file,
            config,
            is_tooling_crate,
        }));
    }
    for file in &test_scan.files {
        violations.extend(scanning::check_test_file(repo_root, &tests_root, file));
    }
    violations.extend(containers::check_containers(&src_scan.files));
    violations.extend(domains::check_domains(&src_scan.files));
    violations.extend(ownership::check(
        crate_dir,
        workspace_crate.package_name.as_deref(),
        &src_scan.files,
    ));
    violations.extend(surfaces::check(&src_scan.files));
    if is_tooling_crate {
        violations.extend(tooling::check(&src_scan.files));
    }
    violations.extend(test_mirroring::check_test_mirroring(repo_root, crate_dir));
    violations.extend(test_mirroring::check_harness_coverage(repo_root, crate_dir));
    violations.extend(layers::check_manifest(repo_root, crate_dir, config));
    violations
}
