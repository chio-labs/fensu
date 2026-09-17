//! Analyze a Cargo workspace with explicit ownership roots.

use std::path::Path;

use crate::models::RepositoryAnalysis;

/// Analyze a Cargo workspace using concrete repository-relative ownership roots.
pub fn analyze_repository_with_ownership_roots(
    repository_root: &Path,
    options: Option<&toml::map::Map<String, toml::Value>>,
    tooling: &[String],
    ownership_roots: &[String],
) -> Result<RepositoryAnalysis, String> {
    crate::engine::_helpers::repository_analysis::analyze(
        repository_root,
        options,
        tooling,
        ownership_roots,
    )
}
