//! Analyze a Cargo workspace behind an owned diagnostic boundary.

use std::path::Path;

use fensu_structure_checker::configuration::main::load_checker_config::load_checker_config;
use fensu_structure_checker::models::CheckerConfig;
use fensu_structure_checker::rules::main::check_repository_with_config::check_repository_with_config;

use crate::models::{AnalysisDiagnostic, RepositoryAnalysis};

/// Analyze one Cargo workspace using built-in or explicit versioned structure policy.
pub fn analyze_repository(
    repository_root: &Path,
    config_path: Option<&Path>,
) -> Result<RepositoryAnalysis, String> {
    let config = config_path.map_or_else(|| Ok(CheckerConfig::default()), load_checker_config)?;
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
