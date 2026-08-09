//! Resolve configuration and discover the sources a check will evaluate.

use std::env;
use std::fs;
use std::path::Path;

use walkdir::WalkDir;

use crate::catalogue::main::rule_catalogue::configured_rule_catalogue;
use crate::check::_helpers::options::use_color;
use crate::check::_helpers::policy::{
    check_identity, hex_digest, path_matches, validate_scope_roots,
};
use crate::check::_helpers::rule_policy::validate_config_tiers;
use crate::check::models::{CheckIdentityRequest, CheckPlan, CheckPlans};
use crate::configuration::main::load_targets;
use crate::configuration::main::resolve_target_root::resolve_target_root;
use crate::configuration::main::validate_exception_targets::validate_exception_targets;
use crate::constants::PYTHON_CACHE_DIRECTORY;
use crate::models::{CheckOptions, Config, ScopedSource};

pub(crate) fn prepare_checks(options: &CheckOptions) -> Result<CheckPlans, String> {
    let invocation = env::current_dir()
        .map_err(|error| error.to_string())?
        .canonicalize()
        .map_err(|error| error.to_string())?;
    let loaded = load_targets::load_targets(&invocation, options.target.as_deref())?;
    if loaded.len() > 1 && !options.paths.is_empty() {
        return Err(
            "Positional paths require exactly one selected target; use --target TARGET.".to_owned(),
        );
    }
    let mut plans = Vec::with_capacity(loaded.len());
    for (config_path, mut config) in loaded {
        let root = config_path
            .parent()
            .ok_or_else(|| "Configuration has no parent directory.".to_owned())?
            .canonicalize()
            .map_err(|error| error.to_string())?;
        let project_root = resolve_target_root(&root, &config.target_root)?;
        if !options.paths.is_empty() {
            config.roots = configured_paths(options, &invocation, &project_root)?;
        }
        validate_config_tiers(&config)?;
        validate_exception_codes(&config)?;
        validate_scope_roots(&project_root, &config)?;
        validate_exception_targets(&config, &project_root)?;
        let discovered = discover(&root, &project_root, &config)?;
        let (sources, excluded) = select_sources(discovered, &config);
        let cache_enabled = options.cache_enabled.unwrap_or(config.cache_enabled);
        let color = use_color(&options.color);
        let identity = check_identity(CheckIdentityRequest {
            root: &root,
            project_root: &project_root,
            config: &config,
            sources: &sources,
            warnings: options.warn,
        });
        plans.push(CheckPlan {
            root,
            project_root,
            config,
            sources,
            excluded,
            identity,
            cache_enabled,
            color,
        });
    }
    let first = plans
        .first()
        .ok_or_else(|| "No analyzer targets were selected.".to_owned())?;
    let root = first.root.clone();
    let color = first.color;
    let cache_enabled = plans.iter().all(|plan| plan.cache_enabled);
    let identity = if plans.len() == 1 {
        first.identity.clone()
    } else {
        let mut combined: Vec<u8> = Vec::new();
        for plan in &plans {
            combined
                .extend_from_slice(plan.config.target.as_deref().unwrap_or_default().as_bytes());
            combined.push(0);
            combined.extend_from_slice(plan.identity.as_bytes());
            combined.push(0);
        }
        hex_digest(&combined)
    };
    let mut sources = plans
        .iter()
        .flat_map(|plan| plan.sources.iter().cloned())
        .collect::<Vec<_>>();
    sources.sort_by(|left, right| left.repository_path.cmp(&right.repository_path));
    sources.dedup_by(|left, right| left.repository_path == right.repository_path);
    Ok(CheckPlans {
        invocation,
        root,
        plans,
        sources,
        identity,
        cache_enabled,
        color,
    })
}

fn validate_exception_codes(config: &Config) -> Result<(), String> {
    let known = configured_rule_catalogue(&config.rule_packs)?
        .into_iter()
        .map(|rule| rule.code.as_str())
        .collect::<std::collections::HashSet<_>>();
    if let Some(exception) = config.exceptions.iter().find(|exception| {
        let hosted_custom = exception.rule.starts_with('X')
            && (!config.rule_paths.is_empty() || !config.rule_modules.is_empty());
        !hosted_custom && !known.contains(exception.rule.as_str())
    }) {
        return Err(format!(
            "Rule exception references unknown rule code: {}.",
            exception.rule
        ));
    }
    Ok(())
}

fn configured_paths(
    options: &CheckOptions,
    invocation: &Path,
    root: &Path,
) -> Result<Vec<String>, String> {
    let mut configured: Vec<String> = Vec::new();
    for path in &options.paths {
        let absolute = invocation
            .join(path)
            .canonicalize()
            .map_err(|error| error.to_string())?;
        let relative = absolute
            .strip_prefix(root)
            .map_err(|error| error.to_string())?;
        configured.push(relative.to_string_lossy().replace('\\', "/"));
    }
    Ok(configured)
}

fn discover(
    root: &Path,
    project_root: &Path,
    config: &Config,
) -> Result<Vec<ScopedSource>, String> {
    let mut sources: Vec<ScopedSource> = Vec::new();
    for (scope, configured_root) in config
        .roots
        .iter()
        .map(|path| ("root", path))
        .chain(config.tests.iter().map(|path| ("test", path)))
        .chain(config.tooling.iter().map(|path| ("tooling", path)))
    {
        let source_root = project_root.join(configured_root);
        if !source_root.exists() {
            continue;
        }
        for entry in WalkDir::new(&source_root)
            .into_iter()
            .filter_entry(|entry| entry.file_name() != PYTHON_CACHE_DIRECTORY)
            .filter_map(Result::ok)
        {
            if !entry.file_type().is_file()
                || entry.path().extension().and_then(|value| value.to_str()) != Some("py")
            {
                continue;
            }
            let path = entry.path().to_path_buf();
            let content = fs::read(&path).map_err(|error| error.to_string())?;
            let repository_path = path
                .strip_prefix(root)
                .map_err(|error| error.to_string())?
                .to_string_lossy()
                .replace('\\', "/");
            let target_path = path
                .strip_prefix(project_root)
                .map_err(|error| error.to_string())?
                .to_string_lossy()
                .replace('\\', "/");
            let relative_parts: Vec<String> = path
                .strip_prefix(&source_root)
                .map_err(|error| error.to_string())?
                .components()
                .map(|part| part.as_os_str().to_string_lossy().into_owned())
                .collect();
            sources.push(ScopedSource {
                path,
                repository_path,
                target_path,
                root: source_root.clone(),
                root_text: configured_root.clone(),
                scope: scope.to_owned(),
                relative_parts,
                fingerprint: hex_digest(&content),
                content,
                program: None,
            });
        }
    }
    sources.sort_by(|left, right| {
        left.repository_path
            .cmp(&right.repository_path)
            .then_with(|| {
                right
                    .root
                    .components()
                    .count()
                    .cmp(&left.root.components().count())
            })
    });
    sources.dedup_by(|left, right| left.repository_path == right.repository_path);
    Ok(sources)
}

fn select_sources(sources: Vec<ScopedSource>, config: &Config) -> (Vec<ScopedSource>, usize) {
    let discovered = sources.len();
    let mut selected: Vec<ScopedSource> = Vec::new();
    for source in sources {
        let included = config.evaluation_include.is_empty()
            || config
                .evaluation_include
                .iter()
                .any(|pattern| path_matches(&source.target_path, pattern));
        let excluded = config
            .evaluation_exclude
            .iter()
            .any(|pattern| path_matches(&source.target_path, pattern));
        if included && !excluded {
            selected.push(source);
        }
    }
    let excluded = discovered - selected.len();
    (selected, excluded)
}
