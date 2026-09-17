//! Analyze a Cargo workspace behind an owned diagnostic boundary.

use std::path::Path;

use crate::models::RepositoryAnalysis;

/// Analyze a Cargo workspace using the normal Fensu rule options.
pub fn analyze_repository(
    repository_root: &Path,
    options: Option<&toml::map::Map<String, toml::Value>>,
    tooling: &[String],
) -> Result<RepositoryAnalysis, String> {
    crate::engine::_helpers::repository_analysis::analyze(repository_root, options, tooling, &[])
}
