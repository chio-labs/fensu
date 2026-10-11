//! Check direct package entries against the Cargo layout allow-list.

use std::path::Path;

use crate::rules::_helpers::repository::package_entries;
use crate::{constants, models};

pub(crate) fn check(
    root: &Path,
    crates: &[models::WorkspaceCrate],
    config: &models::RustPolicy,
) -> Vec<models::Violation> {
    let mut violations: Vec<models::Violation> = Vec::new();
    for package in crates {
        match check_package(root, &package.directory, crates, config) {
            Ok(found) => violations.extend(found),
            Err(error) => violations.push(models::Violation::new(models::ViolationRequest {
                code: constants::PACKAGE_CONTENTS_CODE,
                path: package
                    .directory
                    .strip_prefix(root)
                    .unwrap_or(&package.directory),
                line: None,
                message: error,
                remediation: "restore readable package entries and valid repository ignore files",
            })),
        }
    }
    violations
}

fn check_package(
    root: &Path,
    package: &Path,
    crates: &[models::WorkspaceCrate],
    config: &models::RustPolicy,
) -> Result<Vec<models::Violation>, String> {
    let matchers = package_entries::matchers(root, package)?;
    let mut violations: Vec<models::Violation> = Vec::new();
    for entry in package_entries::entries(package)? {
        let path = entry.path();
        let directory = entry
            .file_type()
            .map_err(|error| error.to_string())?
            .is_dir();
        if entry.file_name() == constants::CARGO_LOCK_FILE
            || entry.file_name() == constants::TARGET_KEY && directory
            || package_entries::ignored(&path, directory, &matchers)
            || crates
                .iter()
                .any(|other| other.directory != package && other.directory.starts_with(&path))
            || allowed(&path, directory, &config.crate_allowed_entries)
        {
            continue;
        }
        violations.push(models::Violation::new(models::ViolationRequest {
            code: constants::PACKAGE_CONTENTS_CODE,
            path: path.strip_prefix(root).unwrap_or(&path),
            line: None,
            message: "package directory contains a non-standard entry",
            remediation: "move data into its owning source domain or configure allowed_entries",
        }));
    }
    Ok(violations)
}

fn allowed(path: &Path, directory: bool, patterns: &[String]) -> bool {
    patterns.iter().any(|pattern| {
        if pattern.ends_with('/') && !directory {
            return false;
        }
        globset::Glob::new(pattern.trim_end_matches('/')).is_ok_and(|glob| {
            glob.compile_matcher()
                .is_match(Path::new(path.file_name().unwrap_or_default()))
        })
    })
}
