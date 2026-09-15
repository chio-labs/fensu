//! Check every workspace crate under explicit consumer configuration.

use std::path;

use crate::models;
use crate::rules::_helpers::repository::project_checks;
use crate::rules::_helpers::sources::scanning;

/// Check a workspace using explicit consumer identities and boundaries.
pub fn check_repository_with_config(
    repo_root: &path::Path,
    config: &models::RustPolicy,
) -> Result<Vec<models::Violation>, String> {
    config.validate()?;
    let repo_root = repo_root
        .canonicalize()
        .map_err(|error| format!("could not canonicalize repository root: {error}"))?;
    let workspace = scanning::scan_workspace(&repo_root);
    let mut violations = project_checks::check_scan(&repo_root, workspace, config);
    violations.sort_by(|left, right| left.sort_key().cmp(&right.sort_key()));
    Ok(violations)
}
