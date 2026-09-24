//! Resolve configuration and discover the sources a check will evaluate.

use std::collections::HashMap;
use std::env;
use std::fs;
use std::path::{Path, PathBuf};

use walkdir::WalkDir;

use crate::analyzer::AnalyzerId;
use crate::catalogue::main::rule_catalogue::configured_rule_catalogue;
use crate::check::_helpers::options::use_color;
use crate::check::_helpers::policy::{
    check_identity, hex_digest, path_matches, validate_scope_roots,
};
use crate::check::_helpers::project as web;
use crate::check::_helpers::rule_policy::validate_config_tiers;
use crate::check::constants::{CARGO_TARGET_DIRECTORY, GIT_DIRECTORY};
use crate::check::models::{CheckIdentityRequest, CheckPlan, CheckPlans};
use crate::configuration::main::load_targets;
use crate::configuration::main::resolve_target_root::resolve_target_root;
use crate::configuration::main::validate_exception_targets::validate_exception_targets;
use crate::constants::CUSTOM_RULE_TEST_COVERAGE_CODE;
use crate::constants::{CURRENT_PATH, PYTHON_CACHE_DIRECTORY, SCOPE_ROOT, SCOPE_TEST};
use crate::models::{CheckOptions, Config, ResolvedOwnershipRoot, ScopedSource, SourcePurpose};
use crate::repository_io::main::relative_path::relative_path;

include!("preparation_ownership.inc");

pub(crate) fn prepare_checks(
    options: &CheckOptions,
    target_names: Option<&std::collections::HashSet<String>>,
) -> Result<CheckPlans, String> {
    let invocation = dunce::canonicalize(env::current_dir().map_err(|error| error.to_string())?)
        .map_err(|error| error.to_string())?;
    let mut loaded = load_targets::load_targets(&invocation, options.target.as_deref())?;
    if let Some(target_names) = target_names {
        loaded.retain(|(_, config)| {
            config
                .target
                .as_ref()
                .is_some_and(|target| target_names.contains(target))
        });
    }
    if loaded.len() > 1 && !options.paths.is_empty() {
        return Err(
            "Positional paths require exactly one selected target; use --target TARGET.".to_owned(),
        );
    }
    let mut plans = Vec::with_capacity(loaded.len());
    for (config_path, mut config) in loaded {
        let root = dunce::canonicalize(
            config_path
                .parent()
                .ok_or_else(|| "Configuration has no parent directory.".to_owned())?,
        )
        .map_err(|error| error.to_string())?;
        let project_root = resolve_target_root(&root, &config.target_root)?;
        if config.analyzer == crate::analyzer::AnalyzerId::Rust && !options.paths.is_empty() {
            return Err(
                "Positional paths are not supported by repository-level Rust checks; use evaluation include/exclude policy."
                    .to_owned(),
            );
        }
        if !options.paths.is_empty() {
            config.roots = configured_paths(options, &invocation, &project_root)?;
        }
        validate_config_tiers(&config)?;
        validate_exception_codes(&config)?;
        validate_scope_roots(&project_root, &config)?;
        validate_exception_targets(&config, &project_root)?;
        config.resolved_ownership_roots = resolve_ownership_roots(&project_root, &config)?;
        let discovered = discover(&root, &project_root, &config)?;
        let (sources, excluded) = select_sources(discovered, &config);
        let mut project_inputs = match config.analyzer {
            crate::analyzer::AnalyzerId::Python => Vec::new(),
            crate::analyzer::AnalyzerId::Rust => {
                rust_project_inputs(&root, &project_root, &config)?
            }
            _ => web::discover_project_inputs(&root, &project_root, &config)?,
        };
        if matches!(
            config.analyzer,
            crate::analyzer::AnalyzerId::TypeScript | crate::analyzer::AnalyzerId::Svelte
        ) {
            project_inputs.extend(custom_rule_project_inputs(&root, &project_root, &config)?);
            project_inputs.sort_by(|left, right| left.repository_path.cmp(&right.repository_path));
            project_inputs.dedup_by(|left, right| left.path == right.path);
        }
        if config.analyzer != crate::analyzer::AnalyzerId::Python
            && custom_rule_coverage_selected(&config, options.warn)
        {
            project_inputs.extend(custom_rule_test_inputs(&root, &project_root, &config)?);
            project_inputs.sort_by(|left, right| left.repository_path.cmp(&right.repository_path));
            project_inputs.dedup_by(|left, right| left.path == right.path);
        }
        let cache_enabled = options.cache_enabled.unwrap_or(config.cache_enabled)
            && (!matches!(
                config.analyzer,
                crate::analyzer::AnalyzerId::Rust
                    | crate::analyzer::AnalyzerId::TypeScript
                    | crate::analyzer::AnalyzerId::Svelte
            ) || custom_cache_inputs_complete(&project_root, &config));
        let color = use_color(&options.color);
        let identity = check_identity(CheckIdentityRequest {
            root: &root,
            project_root: &project_root,
            config: &config,
            sources: &sources,
            project_inputs: &project_inputs,
            warnings: options.warn,
        })?;
        plans.push(CheckPlan {
            root,
            project_root,
            config,
            sources,
            project_inputs,
            excluded,
            identity,
            cache_enabled,
            color,
            repository_facts: None,
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
            for value in [
                plan.config.analyzer.to_string(),
                plan.config.target.clone().unwrap_or_default(),
                plan.config.target_root.clone(),
                plan.identity.clone(),
            ] {
                combined.extend_from_slice(&value.len().to_be_bytes());
                combined.extend_from_slice(value.as_bytes());
            }
        }
        hex_digest(&combined)
    };
    let mut sources = plans
        .iter()
        .flat_map(|plan| plan.sources.iter().cloned())
        .collect::<Vec<_>>();
    sources.sort_by(|left, right| {
        (
            left.analyzer.to_string(),
            &left.target_identity,
            &left.repository_path,
        )
            .cmp(&(
                right.analyzer.to_string(),
                &right.target_identity,
                &right.repository_path,
            ))
    });
    sources.dedup_by(|left, right| {
        left.analyzer == right.analyzer
            && left.target_identity == right.target_identity
            && left.repository_path == right.repository_path
            && left.parser_contract == right.parser_contract
    });
    Ok(CheckPlans {
        invocation,
        config_target: options.target.clone(),
        check_skill_freshness: target_names.is_none(),
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
        let absolute =
            dunce::canonicalize(invocation.join(path)).map_err(|error| error.to_string())?;
        let relative = relative_path(&absolute, root)
            .ok_or_else(|| format!("Positional path must resolve inside the target: {path}"))?;
        configured.push(relative.to_string_lossy().replace('\\', "/"));
    }
    Ok(configured)
}

pub(crate) fn discover(
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
        let candidate = project_root.join(configured_root);
        let source_root = if candidate.exists() {
            dunce::canonicalize(&candidate).map_err(|error| {
                format!("Could not resolve configured source root {configured_root}: {error}")
            })?
        } else {
            candidate
        };
        if relative_path(&source_root, project_root).is_none() {
            return Err(format!(
                "Configured source root must resolve inside the target: {configured_root}"
            ));
        }
        if !source_root.exists() {
            continue;
        }
        for result in WalkDir::new(&source_root)
            .follow_links(false)
            .into_iter()
            .filter_entry(|entry| match config.analyzer {
                crate::analyzer::AnalyzerId::Python => entry.file_name() != PYTHON_CACHE_DIRECTORY,
                crate::analyzer::AnalyzerId::Rust => {
                    entry.file_name() != CARGO_TARGET_DIRECTORY
                        && entry.file_name() != GIT_DIRECTORY
                }
                _ => web::is_artifact_entry(entry),
            })
        {
            let entry = result.map_err(|error| {
                format!("Could not discover sources under {configured_root}: {error}")
            })?;
            let supported = match config.analyzer {
                crate::analyzer::AnalyzerId::Python => {
                    entry.path().extension().and_then(|value| value.to_str()) == Some("py")
                }
                crate::analyzer::AnalyzerId::Rust => {
                    entry.path().extension().and_then(|value| value.to_str()) == Some("rs")
                }
                analyzer => web::is_web_source(entry.path(), analyzer),
            };
            if !entry.file_type().is_file() || !supported {
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
            let purpose = if config
                .generated
                .iter()
                .any(|pattern| path_matches(&target_path, pattern))
            {
                SourcePurpose::Generated
            } else if config.analyzer == crate::analyzer::AnalyzerId::Rust
                || web::is_direct_source(entry.path(), config.analyzer)
            {
                SourcePurpose::Direct
            } else {
                SourcePurpose::Support
            };
            let source_scope = if config.analyzer != crate::analyzer::AnalyzerId::Python
                && config.test_layout == crate::models::TestLayout::Colocated
                && scope != SCOPE_TEST
                && web::is_web_test_source(entry.path())
            {
                "test"
            } else {
                scope
            };
            let effective_ownership_root = (source_scope == SCOPE_ROOT)
                .then(|| effective_ownership_root(&target_path, config))
                .flatten();
            sources.push(ScopedSource {
                analyzer: config.analyzer,
                target_identity: config.target.clone().unwrap_or_default(),
                parser_contract: config.analyzer.parser_contract(),
                path,
                repository_path,
                target_path: target_path.clone(),
                test_owner_path: None,
                root: source_root.clone(),
                root_text: configured_root.clone(),
                scope: source_scope.to_owned(),
                relative_parts,
                ownership_root: effective_ownership_root.map(|root| root.path.clone()),
                ownership_root_declaration: effective_ownership_root
                    .map(|root| root.declaration.clone()),
                ownership_relative_parts: effective_ownership_root.map_or_else(Vec::new, |root| {
                    ownership_relative_parts(&target_path, &root.path)
                }),
                fingerprint: hex_digest(&content),
                content,
                purpose,
                imports: Vec::new(),
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
    if config.test_layout == crate::models::TestLayout::Colocated {
        assign_colocated_test_owners(&mut sources, config);
    } else {
        assign_mirrored_test_owners(&mut sources, config);
    }
    inherit_test_ownership(&mut sources, config);
    Ok(sources)
}

fn assign_mirrored_test_owners(sources: &mut [ScopedSource], config: &Config) {
    for source in sources
        .iter_mut()
        .filter(|source| source.scope == SCOPE_TEST)
    {
        if source.test_owner_path.is_none() {
            source.test_owner_path = projected_runtime_path(&source.target_path, config);
        }
    }
}

fn inherit_test_ownership(sources: &mut [ScopedSource], config: &Config) {
    for source in sources
        .iter_mut()
        .filter(|source| source.scope == SCOPE_TEST)
    {
        let Some(owner_path) = source.test_owner_path.as_deref() else {
            continue;
        };
        let Some(root) = effective_ownership_root(owner_path, config) else {
            continue;
        };
        source.ownership_root = Some(root.path.clone());
        source.ownership_root_declaration = Some(root.declaration.clone());
        source.ownership_relative_parts = ownership_relative_parts(owner_path, &root.path);
    }
}

fn projected_runtime_path(path: &str, config: &Config) -> Option<String> {
    let relative = config
        .tests
        .iter()
        .filter_map(|root| {
            path.strip_prefix(root)
                .and_then(|value| value.strip_prefix('/'))
        })
        .min_by_key(|value| value.len())?;
    let relative = without_test_scope(relative, &config.test_scopes);
    if config
        .roots
        .iter()
        .any(|root| relative == root || relative.starts_with(&format!("{root}/")))
    {
        return Some(relative.to_owned());
    }
    let [root] = config.roots.as_slice() else {
        return None;
    };
    Some(format!("{root}/{relative}"))
}

fn without_test_scope<'a>(relative: &'a str, test_scopes: &[String]) -> &'a str {
    let Some((scope, remainder)) = relative.split_once('/') else {
        return relative;
    };
    if test_scopes.iter().any(|value| value == scope) {
        remainder
    } else {
        relative
    }
}

fn rust_project_inputs(
    repository_root: &Path,
    project_root: &Path,
    config: &Config,
) -> Result<Vec<crate::models::ProjectInput>, String> {
    let mut inputs: Vec<crate::models::ProjectInput> = Vec::new();
    for result in WalkDir::new(project_root)
        .follow_links(false)
        .into_iter()
        .filter_entry(|entry| {
            entry.file_name() != CARGO_TARGET_DIRECTORY && entry.file_name() != GIT_DIRECTORY
        })
    {
        let entry = result.map_err(|error| format!("Could not discover Cargo inputs: {error}"))?;
        let cargo_input = matches!(
            entry.file_name().to_str(),
            Some("Cargo.toml" | "Cargo.lock")
        );
        let rust_source = entry.path().extension().and_then(|value| value.to_str()) == Some("rs");
        if !entry.file_type().is_file() || !(cargo_input || rust_source) {
            continue;
        }
        inputs.push(project_input(entry.path(), repository_root, project_root)?);
    }
    inputs.extend(custom_rule_project_inputs(
        repository_root,
        project_root,
        config,
    )?);
    inputs.sort_by(|left, right| left.repository_path.cmp(&right.repository_path));
    inputs.dedup_by(|left, right| left.path == right.path);
    Ok(inputs)
}

fn custom_rule_project_inputs(
    repository_root: &Path,
    project_root: &Path,
    config: &Config,
) -> Result<Vec<crate::models::ProjectInput>, String> {
    let mut inputs: Vec<crate::models::ProjectInput> = Vec::new();
    for configured in &config.rule_paths {
        let Some(path) = local_custom_rule_path(project_root, configured) else {
            continue;
        };
        if path.is_file() {
            inputs.push(project_input(&path, repository_root, project_root)?);
        } else if path.is_dir() {
            for entry in WalkDir::new(&path).follow_links(false) {
                let entry = entry
                    .map_err(|error| format!("Could not discover custom rule inputs: {error}"))?;
                if entry.file_type().is_file()
                    && entry.path().extension().and_then(|value| value.to_str()) == Some("py")
                {
                    inputs.push(project_input(entry.path(), repository_root, project_root)?);
                }
            }
        }
    }
    for module in &config.rule_modules {
        let package_root = project_root.join(module.split('.').next().unwrap_or_default());
        if !package_root.is_dir() {
            continue;
        }
        for entry in WalkDir::new(package_root).follow_links(false) {
            let entry = entry
                .map_err(|error| format!("Could not discover custom module inputs: {error}"))?;
            if entry.file_type().is_file()
                && entry.path().extension().and_then(|value| value.to_str()) == Some("py")
            {
                inputs.push(project_input(entry.path(), repository_root, project_root)?);
            }
        }
    }
    Ok(inputs)
}

fn custom_rule_test_inputs(
    repository_root: &Path,
    project_root: &Path,
    config: &Config,
) -> Result<Vec<crate::models::ProjectInput>, String> {
    let mut inputs: Vec<crate::models::ProjectInput> = Vec::new();
    for configured in &config.tests {
        let root = project_root.join(configured);
        if !root.is_dir() {
            continue;
        }
        for entry in WalkDir::new(root).follow_links(false) {
            let entry =
                entry.map_err(|error| format!("Could not discover custom rule tests: {error}"))?;
            if entry.file_type().is_file()
                && entry.path().extension().and_then(|value| value.to_str()) == Some("py")
            {
                inputs.push(project_input(entry.path(), repository_root, project_root)?);
            }
        }
    }
    Ok(inputs)
}

fn custom_rule_coverage_selected(config: &Config, show_warnings: bool) -> bool {
    let configured = !config.rule_paths.is_empty() || !config.rule_modules.is_empty();
    let ignored = config
        .ignore
        .iter()
        .any(|selector| CUSTOM_RULE_TEST_COVERAGE_CODE.starts_with(selector));
    configured
        && !ignored
        && (config
            .select
            .iter()
            .any(|selector| CUSTOM_RULE_TEST_COVERAGE_CODE.starts_with(selector))
            || show_warnings
                && config
                    .warn
                    .iter()
                    .any(|selector| CUSTOM_RULE_TEST_COVERAGE_CODE.starts_with(selector)))
}

fn custom_cache_inputs_complete(project_root: &Path, config: &Config) -> bool {
    config
        .rule_paths
        .iter()
        .all(|path| local_custom_rule_path(project_root, path).is_some())
        && config.rule_modules.iter().all(|module| {
            project_root
                .join(module.split('.').next().unwrap_or_default())
                .is_dir()
        })
}

fn local_custom_rule_path(project_root: &Path, configured: &str) -> Option<PathBuf> {
    let configured_path = Path::new(configured);
    let candidate = if configured_path.is_absolute() {
        configured_path.to_path_buf()
    } else {
        project_root.join(configured_path)
    };
    let canonical = match dunce::canonicalize(candidate) {
        Ok(path) => path,
        Err(_) => return None,
    };
    if !canonical.starts_with(project_root) {
        return None;
    }
    Some(canonical)
}

fn project_input(
    path: &Path,
    repository_root: &Path,
    project_root: &Path,
) -> Result<crate::models::ProjectInput, String> {
    let path = dunce::canonicalize(path).map_err(|error| error.to_string())?;
    let content = fs::read(&path).map_err(|error| error.to_string())?;
    let repository_path = path
        .strip_prefix(repository_root)
        .map_err(|_| {
            format!(
                "Rust project input escapes the repository: {}.",
                path.display()
            )
        })?
        .to_string_lossy()
        .replace('\\', "/");
    let target_path = path
        .strip_prefix(project_root)
        .map_err(|_| format!("Rust project input escapes the target: {}.", path.display()))?
        .to_string_lossy()
        .replace('\\', "/");
    Ok(crate::models::ProjectInput {
        path,
        extended_configs: Vec::new(),
        repository_path,
        target_path,
        fingerprint: hex_digest(&content),
        content,
        present: true,
    })
}

fn assign_colocated_test_owners(sources: &mut [ScopedSource], config: &Config) {
    let owners = sources
        .iter()
        .filter(|source| source.scope != SCOPE_TEST)
        .map(|source| (source.target_path.clone(), source.path.clone()))
        .collect::<Vec<_>>();
    for source in sources
        .iter_mut()
        .filter(|source| source.scope == SCOPE_TEST)
    {
        if !config
            .roots
            .iter()
            .chain(&config.tooling)
            .any(|root| source.target_path.starts_with(&format!("{root}/")))
        {
            continue;
        }
        let Some(identity) = web::web_test_identity(&source.path) else {
            continue;
        };
        source.test_owner_path = owners
            .iter()
            .filter(|(_, path)| path.parent() == source.path.parent())
            .find(|(_, path)| web::web_source_identity(path).as_deref() == Some(&identity))
            .map(|(target_path, _)| target_path.clone());
    }
}

pub(crate) fn select_sources(
    sources: Vec<ScopedSource>,
    config: &Config,
) -> (Vec<ScopedSource>, usize) {
    if config.analyzer != crate::analyzer::AnalyzerId::Python {
        let mut excluded = 0;
        let mut retained = Vec::with_capacity(sources.len());
        for mut source in sources {
            let evaluated: bool = source.purpose.is_direct()
                || config.analyzer == crate::analyzer::AnalyzerId::Svelte
                    && source.purpose == SourcePurpose::Support
                    && web::is_direct_source(&source.path, crate::analyzer::AnalyzerId::TypeScript);
            if evaluated && !selected_by_evaluation(&source, config) {
                source.purpose = SourcePurpose::Excluded;
                excluded += 1;
            }
            retained.push(source);
        }
        return (retained, excluded);
    }
    let discovered = sources.len();
    let mut selected: Vec<ScopedSource> = Vec::new();
    for source in sources {
        if selected_by_evaluation(&source, config) {
            selected.push(source);
        }
    }
    let excluded = discovered - selected.len();
    (selected, excluded)
}

fn selected_by_evaluation(source: &ScopedSource, config: &Config) -> bool {
    let included = config.evaluation_include.is_empty()
        || config
            .evaluation_include
            .iter()
            .any(|pattern| path_matches(&source.target_path, pattern));
    let excluded = config
        .evaluation_exclude
        .iter()
        .any(|pattern| path_matches(&source.target_path, pattern));
    included && !excluded
}
