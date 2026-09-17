//! Analyze a Cargo workspace with an explicit ownership depth.

use std::path::Path;

use crate::models::RepositoryAnalysis;

/// Analyze a Cargo workspace using a configured ownership depth.
pub fn analyze_repository_with_ownership_depth(
    repository_root: &Path,
    options: Option<&toml::map::Map<String, toml::Value>>,
    tooling: &[String],
    ownership_depth: usize,
) -> Result<RepositoryAnalysis, String> {
    crate::engine::_helpers::repository_analysis::analyze(
        repository_root,
        options,
        tooling,
        ownership_depth,
    )
}
