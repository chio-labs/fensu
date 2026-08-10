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
use crate::check::_helpers::project as web;
use crate::check::_helpers::rule_policy::validate_config_tiers;
use crate::check::models::{CheckIdentityRequest, CheckPlan, CheckPlans};
use crate::configuration::main::load_targets;
use crate::configuration::main::resolve_target_root::resolve_target_root;
use crate::configuration::main::validate_exception_targets::validate_exception_targets;
use crate::constants::{PYTHON_CACHE_DIRECTORY, SCOPE_TEST};
use crate::models::{CheckOptions, Config, ScopedSource, SourcePurpose};
use crate::repository_io::main::relative_path::relative_path;

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
        if !options.paths.is_empty() {
            config.roots = configured_paths(options, &invocation, &project_root)?;
        }
        validate_config_tiers(&config)?;
        validate_exception_codes(&config)?;
        validate_scope_roots(&project_root, &config)?;
        validate_exception_targets(&config, &project_root)?;
        let discovered = discover(&root, &project_root, &config)?;
        let (sources, excluded) = select_sources(discovered, &config);
        let project_inputs = if config.analyzer == crate::analyzer::AnalyzerId::Python {
            Vec::new()
        } else {
            web::discover_project_inputs(&root, &project_root, &config)?
        };
        let cache_enabled = options.cache_enabled.unwrap_or(config.cache_enabled);
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
            .filter_entry(|entry| {
                if config.analyzer == crate::analyzer::AnalyzerId::Python {
                    entry.file_name() != PYTHON_CACHE_DIRECTORY
                } else {
                    web::is_artifact_entry(entry)
                }
            })
        {
            let entry = result.map_err(|error| {
                format!("Could not discover sources under {configured_root}: {error}")
            })?;
            let supported = match config.analyzer {
                crate::analyzer::AnalyzerId::Python => {
                    entry.path().extension().and_then(|value| value.to_str()) == Some("py")
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
            } else if web::is_direct_source(entry.path(), config.analyzer) {
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
            sources.push(ScopedSource {
                analyzer: config.analyzer,
                target_identity: config.target.clone().unwrap_or_default(),
                parser_contract: config.analyzer.parser_contract(),
                path,
                repository_path,
                target_path,
                test_owner_path: None,
                root: source_root.clone(),
                root_text: configured_root.clone(),
                scope: source_scope.to_owned(),
                relative_parts,
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
    }
    Ok(sources)
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

fn select_sources(sources: Vec<ScopedSource>, config: &Config) -> (Vec<ScopedSource>, usize) {
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
