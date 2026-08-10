use std::collections::HashSet;
use std::path::{Path, PathBuf};

use crate::configuration::main::resolve_target_root::resolve_target_root;
use crate::configuration::main::validate_exception_targets::validate_exception_targets;
use crate::configuration::main::{load_target, load_targets};
use crate::models::Config;
use crate::repository_io::main::relative_path::relative_path;
use crate::skills::_helpers::context::{exceptions, identity, selection};
use crate::skills::models::{SkillContext, SkillOptions};

const ROOT_SCOPE: &str = "roots";
const RUNTIME_SCOPE_LABEL: &str = "Runtime";

pub(crate) fn build(invocation: &Path, options: &SkillOptions) -> Result<SkillContext, String> {
    let invocation = dunce::canonicalize(invocation).map_err(|error| error.to_string())?;
    if options.config_target.is_some() {
        let loaded = load_target::load_target(&invocation, options.config_target.as_deref())?;
        return build_loaded(&invocation, options, loaded);
    }
    let loaded = load_targets::load_targets(&invocation, None)?;
    let mut contexts = loaded
        .into_iter()
        .map(|target| build_loaded(&invocation, options, target))
        .collect::<Result<Vec<_>, _>>()?;
    if contexts.len() == 1 {
        return contexts
            .pop()
            .ok_or_else(|| "No configured target was loaded.".to_owned());
    }
    aggregate(&invocation, options, contexts)
}

fn build_loaded(
    invocation: &Path,
    options: &SkillOptions,
    loaded: (PathBuf, Config),
) -> Result<SkillContext, String> {
    let (config_path, config) = loaded;
    let config_path = dunce::canonicalize(&config_path)
        .map_err(|error| format!("Could not resolve {}: {error}", config_path.display()))?;
    let repository_root = config_path
        .parent()
        .ok_or_else(|| "Configuration has no parent directory.".to_owned())?
        .to_path_buf();
    let project_root = resolve_target_root(&repository_root, &config.target_root)?;
    selection::validate_config_policy(&config)?;
    validate_layout(&config, &project_root)?;
    let git_root = identity::find_git_root(&project_root);
    let install_root = identity::resolve_install_root(
        options.install_root.as_deref(),
        &project_root,
        invocation,
        git_root.as_deref(),
    )?;
    let project_prefix = relative_path(&project_root, &install_root)
        .map(|path| path.to_string_lossy().replace('\\', "/"))
        .unwrap_or_default();
    let identity =
        identity::resolve_identity(&config, &config_path, &project_root, git_root.as_deref())?;
    let selection = selection::selection(&config, &project_root)?;
    exceptions::validate(&config, &selection.catalogue)?;
    validate_exception_targets(&config, &project_root)?;
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
        targets: Vec::new(),
        migration_contexts: Vec::new(),
    })
}

fn aggregate(
    invocation: &Path,
    options: &SkillOptions,
    mut targets: Vec<SkillContext>,
) -> Result<SkillContext, String> {
    let mut context = targets
        .first()
        .cloned()
        .ok_or_else(|| "No configured target was loaded.".to_owned())?;
    let repository_root = context
        .config_path
        .parent()
        .ok_or_else(|| "Configuration has no parent directory.".to_owned())?
        .to_path_buf();
    let git_root = identity::find_git_root(&repository_root);
    let install_root = identity::resolve_install_root(
        options.install_root.as_deref(),
        &repository_root,
        invocation,
        git_root.as_deref(),
    )?;
    let migration_contexts = targets.clone();
    for target in &mut targets {
        target.install_root.clone_from(&install_root);
        target.git_root.clone_from(&git_root);
        target.project_prefix = relative_path(&target.project_root, &install_root)
            .map(|path| path.to_string_lossy().replace('\\', "/"))
            .unwrap_or_default();
    }
    let common_name = common_skills_name(&targets);
    context.config.skills_name = common_name;
    context.project_root = repository_root;
    context.install_root = install_root;
    context.git_root = git_root;
    context.project_prefix = relative_path(&context.project_root, &context.install_root)
        .map(|path| path.to_string_lossy().replace('\\', "/"))
        .unwrap_or_default();
    context.identity = identity::resolve_identity(
        &context.config,
        &context.config_path,
        &context.project_root,
        context.git_root.as_deref(),
    )?;
    context.targets = targets;
    context.migration_contexts = migration_contexts;
    Ok(context)
}

fn common_skills_name(targets: &[SkillContext]) -> Option<String> {
    let name = targets.first()?.config.skills_name.clone()?;
    for target in targets {
        if target.config.skills_name.as_deref() != Some(name.as_str()) {
            return None;
        }
    }
    Some(name)
}

fn validate_layout(config: &Config, project_root: &Path) -> Result<(), String> {
    let scopes = [
        (ROOT_SCOPE, &config.roots),
        ("tests", &config.tests),
        ("tooling", &config.tooling),
    ];
    let mut resolved_scopes: Vec<(&str, Vec<PathBuf>)> = Vec::new();
    for (name, values) in scopes {
        let mut resolved: Vec<PathBuf> = Vec::new();
        for value in values {
            let path = identity::normalize_absolute(if Path::new(value).is_absolute() {
                PathBuf::from(value)
            } else {
                project_root.join(value)
            });
            if relative_path(&path, project_root).is_none() {
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
