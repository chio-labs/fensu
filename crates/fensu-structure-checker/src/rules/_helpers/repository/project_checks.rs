//! Repository-wide configured-path, visibility, and call-shape checks.

use std::path;

use crate::models;
use crate::rules::_helpers::functions::shape_project;
use crate::rules::_helpers::imports::{layers, visibility};
use crate::rules::_helpers::repository::configured_paths;
use crate::rules::_helpers::roles::{containers, domains, ownership, surfaces, tooling};
use crate::rules::_helpers::sources::scanning;
use crate::rules::_helpers::test_conventions::test_mirroring;

pub(crate) fn check(
    repo_root: &path::Path,
    workspace_crates: &[models::WorkspaceCrate],
    config: &models::CheckerConfig,
) -> Vec<models::Violation> {
    let mut violations = configured_paths::check(repo_root, workspace_crates, &config.repository);
    violations.extend(architecture_checks(repo_root, workspace_crates));
    violations
}

pub(crate) fn check_crate(
    repo_root: &path::Path,
    workspace_crate: &models::WorkspaceCrate,
    config: &models::CheckerConfig,
) -> Vec<models::Violation> {
    let crate_dir = &workspace_crate.directory;
    let is_tooling_crate = workspace_crate.package_name.as_deref() == Some(&config.tooling.package);
    let (mut violations, structural_files) =
        check_crate_files(repo_root, workspace_crate, config, is_tooling_crate);
    violations.extend(check_aggregate_structure(
        workspace_crate,
        &structural_files,
        config,
        is_tooling_crate,
    ));
    violations.extend(check_test_conventions(repo_root, crate_dir));
    violations.extend(layers::check_manifest(repo_root, workspace_crate, config));
    violations
}

fn check_crate_files(
    repo_root: &path::Path,
    workspace_crate: &models::WorkspaceCrate,
    config: &models::CheckerConfig,
    is_tooling_crate: bool,
) -> (Vec<models::Violation>, Vec<models::SourceFile>) {
    let crate_dir = &workspace_crate.directory;
    let mut violations: Vec<models::Violation> = Vec::new();
    let src_scan = scanning::rust_target_files(repo_root, workspace_crate, false);
    let test_scan = scanning::rust_target_files(repo_root, workspace_crate, true);
    let structural_files = src_scan
        .files
        .iter()
        .filter(|file| !config.is_intentional_layout(&file.relative))
        .cloned()
        .collect::<Vec<_>>();
    violations.extend(src_scan.violations);
    violations.extend(test_scan.violations);
    for file in &src_scan.files {
        let src_root = target_root(workspace_crate, file, false).unwrap_or(crate_dir);
        violations.extend(scanning::check_source_file(models::SourceCheckRequest {
            repo_root,
            src_root,
            file,
            config,
            dependencies: &workspace_crate.dependencies,
            is_tooling_crate,
        }));
    }
    for file in &test_scan.files {
        let tests_root = target_root(workspace_crate, file, true).unwrap_or(crate_dir);
        violations.extend(scanning::check_test_file(models::TestCheckRequest {
            repo_root,
            tests_root,
            file,
            config,
            dependencies: &workspace_crate.dependencies,
        }));
    }
    (violations, structural_files)
}

fn target_root<'a>(
    workspace_crate: &'a models::WorkspaceCrate,
    file: &models::SourceFile,
    test: bool,
) -> Option<&'a path::Path> {
    workspace_crate
        .targets
        .iter()
        .filter(|target| target.test == test && file.path.starts_with(&target.source_root))
        .map(|target| target.source_root.as_path())
        .max_by_key(|root| root.components().count())
}

fn check_aggregate_structure(
    workspace_crate: &models::WorkspaceCrate,
    structural_files: &[models::SourceFile],
    config: &models::CheckerConfig,
    is_tooling_crate: bool,
) -> Vec<models::Violation> {
    let mut violations =
        containers::check_containers(structural_files, &config.repository.thresholds);
    violations.extend(domains::check_domains(structural_files));
    violations.extend(ownership::check(
        &workspace_crate.directory,
        workspace_crate.package_name.as_deref(),
        structural_files,
    ));
    violations.extend(surfaces::check(structural_files));
    if is_tooling_crate {
        violations.extend(tooling::check(structural_files));
    }
    violations
}

fn check_test_conventions(
    repo_root: &path::Path,
    crate_dir: &path::Path,
) -> Vec<models::Violation> {
    let mut violations = test_mirroring::check_test_mirroring(repo_root, crate_dir);
    violations.extend(test_mirroring::check_harness_coverage(repo_root, crate_dir));
    violations
}

fn architecture_checks(
    repo_root: &path::Path,
    workspace_crates: &[models::WorkspaceCrate],
) -> Vec<models::Violation> {
    let mut violations = visibility::check_workspace(repo_root, workspace_crates);
    violations.extend(shape_project::check_workspace(repo_root, workspace_crates));
    violations
}
