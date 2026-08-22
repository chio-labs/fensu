//! Check every workspace crate and return sorted structure violations.

use std::path;

use crate::models;

/// Check the workspace under repo_root and return deterministic violations.
pub fn check_repository(repo_root: &path::Path) -> Vec<models::Violation> {
    match crate::rules::main::check_repository_with_config::check_repository_with_config(
        repo_root,
        &models::CheckerConfig::default(),
    ) {
        Ok(violations) => violations,
        Err(error) => vec![models::Violation::new(models::ViolationRequest {
            code: "RSL901",
            path: path::Path::new("Cargo.toml"),
            line: None,
            message: format!("invalid default structure-checker config: {error}"),
            remediation: "restore the built-in structure-checker configuration",
        })],
    }
}
