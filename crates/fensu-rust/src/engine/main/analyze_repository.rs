//! Analyze a Cargo workspace behind an owned diagnostic boundary.

use std::path::Path;

use crate::configuration::main::rule_options::resolve_rule_options;
use crate::rules::main::check_repository_with_config::check_repository_with_config;

use crate::models::{AnalysisDiagnostic, RepositoryAnalysis};

/// Analyze a Cargo workspace using the normal Fensu rule options.
pub fn analyze_repository(
    repository_root: &Path,
    options: Option<&toml::map::Map<String, toml::Value>>,
    tooling: &[String],
) -> Result<RepositoryAnalysis, String> {
    let mut config = resolve_rule_options(options)?;
    config.tooling.paths = tooling.to_vec();
    let diagnostics: Vec<AnalysisDiagnostic> =
        check_repository_with_config(repository_root, &config)?
            .into_iter()
            .map(|violation| AnalysisDiagnostic {
                code: violation.code,
                path: violation.path,
                line: violation.line,
                message: violation.message,
                remediation: violation.remediation,
            })
            .collect();
    Ok(RepositoryAnalysis { diagnostics })
}
