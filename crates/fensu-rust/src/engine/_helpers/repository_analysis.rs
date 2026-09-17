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
    ownership_roots: &[String],
) -> Result<RepositoryAnalysis, String> {
    let mut config = resolve_rule_options(options)?;
    config.ownership_roots = ownership_roots.to_vec();
    config.tooling.paths = tooling.to_vec();
    config.validate()?;
    let repository_root = repository_root
        .canonicalize()
        .map_err(|error| format!("could not canonicalize repository root: {error}"))?;
    let workspace = scan_workspace(&repository_root);
    validate_ownership_roots(&workspace.crates, ownership_roots)?;
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

fn validate_ownership_roots(
    crates: &[crate::models::WorkspaceCrate],
    ownership_roots: &[String],
) -> Result<(), String> {
    if ownership_roots.is_empty() {
        return Ok(());
    }
    let files = crates
        .iter()
        .flat_map(|workspace_crate| workspace_crate.files.iter())
        .collect::<Vec<_>>();
    for root in ownership_roots {
        let source_root = files
            .iter()
            .map(|file| file.source_root_relative.as_str())
            .filter(|source| root == source || root.starts_with(&format!("{source}/")))
            .max_by_key(|source| source.split('/').count());
        let Some(source_root) = source_root else {
            return Err(format!(
                "ownership root must resolve beneath a Cargo source root: {root}"
            ));
        };
        let relative = root
            .strip_prefix(source_root)
            .and_then(|value| value.strip_prefix('/'))
            .unwrap_or_default();
        if relative
            .split('/')
            .any(|part| crate::constants::CONTAINER_DIRECTORY_NAMES.contains(&part))
        {
            return Err(format!("ownership root crosses a role directory: {root}"));
        }
    }
    let mut used = files
        .iter()
        .filter_map(|file| file.ownership_root(ownership_roots))
        .collect::<Vec<_>>();
    used.sort();
    used.dedup();
    let unused = ownership_roots
        .iter()
        .filter(|root| used.binary_search(root).is_err())
        .map(String::as_str)
        .collect::<Vec<_>>();
    if unused.is_empty() {
        Ok(())
    } else {
        Err(format!("ownership root is unused: {}", unused.join(", ")))
    }
}
