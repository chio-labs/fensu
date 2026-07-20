use std::collections::HashSet;
use std::path::{Path, PathBuf};

use crate::configuration::main::load;
use crate::models::Config;
use crate::skills::helpers::context::{exceptions, identity, selection};
use crate::skills::models::{SkillContext, SkillOptions};

const ROOT_SCOPE: &str = "roots";
const RUNTIME_SCOPE_LABEL: &str = "Runtime";

pub(crate) fn build(invocation: &Path, options: &SkillOptions) -> Result<SkillContext, String> {
    let invocation = invocation
        .canonicalize()
        .map_err(|error| error.to_string())?;
    let (config_path, config) = load::load(&invocation)?;
    let config_path = config_path
        .canonicalize()
        .map_err(|error| format!("Could not resolve {}: {error}", config_path.display()))?;
    let project_root = config_path
        .parent()
        .ok_or_else(|| "Configuration has no parent directory.".to_owned())?
        .to_path_buf();
    selection::validate_config_policy(&config)?;
    validate_layout(&config, &project_root)?;
    let git_root = identity::find_git_root(&project_root);
    let install_root = identity::resolve_install_root(
        options.install_root.as_deref(),
        &project_root,
        &invocation,
        git_root.as_deref(),
    )?;
    let project_prefix = project_root
        .strip_prefix(&install_root)
        .ok()
        .map(|path| path.to_string_lossy().replace('\\', "/"))
        .unwrap_or_default();
    let identity =
        identity::resolve_identity(&config, &config_path, &project_root, git_root.as_deref())?;
    let selection = selection::selection(&config, &project_root)?;
    exceptions::validate(&config, &selection.catalogue, &project_root)?;
    Ok(SkillContext {
        config_path,
        project_root,
        install_root,
        git_root,
        project_prefix,
        identity,
        catalogue: selection.catalogue,
        blocking: selection.blocking,
        warnings: selection.warnings,
        ignored: selection.ignored,
        config,
    })
}

fn validate_layout(config: &Config, project_root: &Path) -> Result<(), String> {
    let scopes = [
        (ROOT_SCOPE, &config.roots),
        ("tests", &config.tests),
        ("tooling", &config.tooling),
    ];
    let mut resolved_scopes = Vec::new();
    for (name, values) in scopes {
        let mut resolved = Vec::new();
        for value in values {
            let path = identity::normalize_absolute(if Path::new(value).is_absolute() {
                PathBuf::from(value)
            } else {
                project_root.join(value)
            });
            if !path.starts_with(project_root) {
                return Err(format!(
                    "Configured path must resolve inside the repository: {value}"
                ));
            }
            resolved.push(path);
        }
        resolved_scopes.push((name, resolved));
    }
    let missing = config
        .roots
        .iter()
        .filter(|value| !project_root.join(value).is_dir())
        .cloned()
        .collect::<Vec<_>>();
    if !missing.is_empty() {
        let mut missing = missing;
        missing.sort();
        return Err(format!(
            "Configured root path(s) do not exist: {}.",
            missing.join(", ")
        ));
    }
    for index in 0..resolved_scopes.len() {
        let (owner, paths) = &resolved_scopes[index];
        for (other_owner, other_paths) in &resolved_scopes[index + 1..] {
            if let Some(duplicate) = paths.iter().filter(|path| other_paths.contains(path)).min() {
                return Err(format!(
                    "Configured path cannot belong to both {owner} and {other_owner}: {}",
                    duplicate.display()
                ));
            }
            let packages = paths
                .iter()
                .filter_map(|path| path.file_name())
                .collect::<HashSet<_>>();
            let mut duplicate_packages = other_paths
                .iter()
                .filter_map(|path| path.file_name())
                .filter(|name| packages.contains(name))
                .map(|name| name.to_string_lossy().into_owned())
                .collect::<Vec<_>>();
            duplicate_packages.sort();
            duplicate_packages.dedup();
            if !duplicate_packages.is_empty() {
                let label = if *owner == ROOT_SCOPE {
                    RUNTIME_SCOPE_LABEL
                } else {
                    owner
                };
                let other_label = if *other_owner == ROOT_SCOPE {
                    RUNTIME_SCOPE_LABEL
                } else {
                    other_owner
                };
                return Err(format!(
                    "{label} and {other_label} roots must not claim the same import package: {}",
                    duplicate_packages.join(", ")
                ));
            }
        }
    }
    Ok(())
}
