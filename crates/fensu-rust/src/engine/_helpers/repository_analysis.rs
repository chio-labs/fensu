//! Shared repository-analysis implementation for public engine entries.

use std::path::Path;

use crate::configuration::main::rule_options::resolve_rule_options;
use crate::facts::main::collect_workspace_facts::collect_workspace_facts;
use crate::models::{AnalysisDiagnostic, RepositoryAnalysis};
use crate::rules::main::check_scanned_workspace::check_scanned_workspace;
use crate::rules::main::scan_workspace::scan_workspace;

pub(crate) fn analyze(
    repository_root: &Path,
    options: Option<&toml::map::Map<String, toml::Value>>,
    tooling: &[String],
    ownership_depth: usize,
) -> Result<RepositoryAnalysis, String> {
    let mut config = resolve_rule_options(options)?;
    config.ownership_depth = ownership_depth.max(crate::constants::MINIMUM_OWNERSHIP_DEPTH);
    config.tooling.paths = tooling.to_vec();
    config.validate()?;
    let repository_root = repository_root
        .canonicalize()
        .map_err(|error| format!("could not canonicalize repository root: {error}"))?;
    let workspace = scan_workspace(&repository_root);
    let facts = collect_workspace_facts(&repository_root, &workspace.crates);
    let mut violations = check_scanned_workspace(&repository_root, workspace, &config);
    violations.sort_by(|left, right| left.sort_key().cmp(&right.sort_key()));
    let diagnostics: Vec<AnalysisDiagnostic> = violations
        .into_iter()
        .map(|violation| AnalysisDiagnostic {
            code: violation.code,
            path: violation.path,
            line: violation.line,
            message: violation.message,
            remediation: violation.remediation,
        })
        .collect();
    Ok(RepositoryAnalysis { diagnostics, facts })
}
