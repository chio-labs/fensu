//! Check direct package entries against the Cargo layout allow-list.

use std::path::Path;

use crate::{constants, models};

pub(crate) fn check(
    repo_root: &Path,
    crates: &[models::WorkspaceCrate],
    config: &models::RustPolicy,
) -> Vec<models::Violation> {
    let mut violations: Vec<models::Violation> = Vec::new();
    for package in crates {
        let entries = ignore::WalkBuilder::new(&package.directory)
            .max_depth(Some(1))
            .require_git(false)
            .build();
        for entry in entries {
            let entry = match entry {
                Ok(entry) => entry,
                Err(error) => {
                    violations.push(models::Violation::new(models::ViolationRequest {
                        code: "RSR311",
                        path: package
                            .directory
                            .strip_prefix(repo_root)
                            .unwrap_or(&package.directory),
                        line: None,
                        message: format!("cannot inspect package entries: {error}"),
                        remediation: "restore a readable package directory",
                    }));
                    continue;
                }
            };
            if entry.depth() == 0
                || entry.file_name() == constants::CARGO_LOCK_FILE
                || entry.file_name() == constants::TARGET_KEY
                    && entry.file_type().is_some_and(|kind| kind.is_dir())
                || crates.iter().any(|other| {
                    other.directory != package.directory
                        && other.directory.starts_with(entry.path())
                })
                || allowed(&entry, &config.crate_allowed_entries)
            {
                continue;
            }
            violations.push(models::Violation::new(models::ViolationRequest {
                code: "RSR311",
                path: entry.path().strip_prefix(repo_root).unwrap_or(entry.path()),
                line: None,
                message: "package directory contains a non-standard entry",
                remediation: "move data into its owning source domain or configure allowed_entries",
            }));
        }
    }
    violations
}

fn allowed(entry: &ignore::DirEntry, patterns: &[String]) -> bool {
    patterns.iter().any(|pattern| {
        if pattern.ends_with('/') && !entry.file_type().is_some_and(|kind| kind.is_dir()) {
            return false;
        }
        globset::Glob::new(pattern.trim_end_matches('/')).is_ok_and(|glob| {
            glob.compile_matcher()
                .is_match(Path::new(entry.file_name()))
        })
    })
}
