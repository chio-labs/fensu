//! Read cached results and render a fresh check run.

use std::collections::HashSet;

use fensu_facts::extension::models::ProgramHandle;

use crate::check::_helpers::cache;
use crate::check::_helpers::evaluation::{evaluate, render_results};
use crate::check::_helpers::policy::python_version;
use crate::check::_helpers::project as web;
use crate::check::models::{
    CheckCacheStats, CheckPlans, CheckResult, CustomRuleSubject, EvaluationRequest,
    RepositoryTargetPayload, StructuredCachePayload, StructuredCheckExecution,
};
use crate::check::repository_custom_facts::python_repository_fact_payload;
use crate::models::{CachedOutput, CheckOptions, CliOutput, Config, ParsedProgram, ScopedSource};
use crate::skills::main::core_freshness;

pub(crate) fn cached_output(plan: &CheckPlans, options: &CheckOptions) -> Option<CliOutput> {
    if !plan.cache_enabled {
        return None;
    }
    let cached = cache::read(&plan.root, &plan.identity, &plan.sources, plan.color)?;
    let mut stderr = String::new();
    if options.cache_stats {
        stderr.push_str(&format!(
            "Cache: hits={} misses=0 invalidations=0 writes=0 non_cacheable=0\n",
            plan.sources.len()
        ));
    }
    stderr.push_str(&freshness(plan));
    Some(CliOutput {
        stdout: cached.output,
        stderr,
        exit_code: cached.exit_code,
    })
}

pub(crate) fn render_check(
    mut plan: CheckPlans,
    options: &CheckOptions,
) -> Result<CliOutput, String> {
    let results = evaluate_checks(&mut plan, options, false)?;
    let cacheable = results
        .iter()
        .all(|result| result.cacheable.unwrap_or(true));
    let (output, exit_code) = render_results(results, &plan.root, plan.color, options.warn);
    let mut stderr = String::new();
    stderr.push_str(&freshness(&plan));
    if plan.cache_enabled && cacheable {
        stderr.push_str(&stored_output(
            &plan,
            &output,
            exit_code,
            options.cache_stats,
        ));
    } else if plan.cache_enabled {
        stderr.push_str("Cache disabled for this run: analysis produced non-cacheable results\n");
        if options.cache_stats {
            stderr.push_str(&format!(
                "Cache: hits=0 misses=0 invalidations=0 writes=0 non_cacheable={}\n",
                plan.sources.len()
            ));
        }
    }
    Ok(CliOutput {
        stdout: output,
        stderr,
        exit_code,
    })
}

pub(crate) fn evaluate_checks(
    plan: &mut CheckPlans,
    options: &CheckOptions,
    collect_repository_facts: bool,
) -> Result<Vec<CheckResult>, String> {
    let mut results = Vec::with_capacity(plan.plans.len());
    for target in &mut plan.plans {
        target.sources = parse_sources(
            &target.config,
            &target.project_root,
            std::mem::take(&mut target.sources),
            &target.project_inputs,
        )?;
        let evaluated = evaluate(EvaluationRequest {
            project_root: &target.project_root,
            config: &target.config,
            sources: &target.sources,
            project_inputs: &target.project_inputs,
            excluded: target.excluded,
            show_warnings: options.warn,
            cache_enabled: target.cache_enabled,
            collect_repository_facts,
        })?;
        target.repository_facts = evaluated.repository_facts;
        results.push(evaluated.result);
    }
    Ok(results)
}

fn stored_output(plan: &CheckPlans, output: &str, exit_code: i32, cache_stats: bool) -> String {
    let cached = CachedOutput {
        identity: plan.identity.clone(),
        output: output.to_owned(),
        exit_code,
        file_count: plan.sources.len(),
    };
    if !cache::write(&plan.root, &cached, &plan.sources, plan.color) {
        return "Cache disabled for this run: cache publication failed\n".to_owned();
    }
    if cache_stats {
        return format!(
            "Cache: hits=0 misses={} invalidations=0 writes={} non_cacheable=0\n",
            plan.sources.len(),
            plan.sources.len()
        );
    }
    String::new()
}

fn freshness(plan: &CheckPlans) -> String {
    if !plan.check_skill_freshness || plan.plans.iter().any(native_custom_policy_is_inactive) {
        return String::new();
    }
    core_freshness::core_freshness(&plan.invocation, plan.config_target.as_deref())
        .unwrap_or_default()
}

fn native_custom_policy_is_inactive(plan: &crate::check::models::CheckPlan) -> bool {
    let config = &plan.config;
    if config.analyzer == crate::analyzer::AnalyzerId::Python {
        return false;
    }
    let custom_configured = !config.rule_paths.is_empty() || !config.rule_modules.is_empty();
    custom_configured
        && !config.select.iter().any(|selector| {
            selector.starts_with('X') && !custom_selector_is_ignored(selector, &config.ignore)
        })
}

fn custom_selector_is_ignored(selector: &str, ignores: &[String]) -> bool {
    ignores
        .iter()
        .any(|ignored| ignored.starts_with('X') && selector.starts_with(ignored))
}

fn parse_sources(
    config: &crate::models::Config,
    project_root: &std::path::Path,
    mut sources: Vec<ScopedSource>,
    project_inputs: &[crate::models::ProjectInput],
) -> Result<Vec<ScopedSource>, String> {
    if config.analyzer == crate::analyzer::AnalyzerId::Rust {
        return Ok(sources);
    }
    if config.analyzer != crate::analyzer::AnalyzerId::Python {
        return web::parse_sources(
            config.analyzer,
            project_root,
            sources,
            project_inputs,
            &config.roots,
        );
    }
    let parsed = ProgramHandle::parse_many(
        sources
            .iter()
            .map(|source| String::from_utf8_lossy(&source.content).into_owned())
            .collect(),
        python_version(),
    );
    for (source, program) in sources.iter_mut().zip(parsed) {
        source.program = Some(ParsedProgram::Python(program.ok_or_else(|| {
            format!("Could not parse Python source: {}", source.repository_path)
        })?));
    }
    Ok(sources)
}

pub(crate) fn structured_checks(
    arguments: &[String],
    target_names: &HashSet<String>,
    collect_repository_facts: bool,
) -> Result<StructuredCheckExecution, String> {
    let options = crate::check::_helpers::options::parse_options(arguments)?;
    let mut plan =
        crate::check::_helpers::preparation::prepare_checks(&options, Some(target_names))?;
    plan.identity.push_str(if collect_repository_facts {
        "-structured-check-repository-v1"
    } else {
        "-structured-check-v1"
    });
    if plan.cache_enabled {
        if let Some(cached) = cache::read(&plan.root, &plan.identity, &plan.sources, false) {
            let payload: StructuredCachePayload = serde_json::from_str(&cached.output)
                .map_err(|error| format!("Invalid structured native cache payload: {error}"))?;
            return Ok(StructuredCheckExecution {
                results: payload.results,
                cache: Some(CheckCacheStats {
                    hits: plan.sources.len(),
                    ..CheckCacheStats::default()
                }),
                messages: Vec::new(),
                root: plan.root,
                color: plan.color,
                show_warnings: options.warn,
                repository_targets: payload.repository_targets,
            });
        }
    }
    fresh_structured_execution(&options, plan, collect_repository_facts)
}

pub(crate) fn repository_python_targets(
    arguments: &[String],
    target_names: &HashSet<String>,
) -> Result<Vec<RepositoryTargetPayload>, String> {
    let options = crate::check::_helpers::options::parse_options(arguments)?;
    let mut plan =
        crate::check::_helpers::preparation::prepare_checks(&options, Some(target_names))?;
    for target in &mut plan.plans {
        if target.config.analyzer != crate::analyzer::AnalyzerId::Python {
            return Err("Repository Python snapshot received a non-Python target.".to_owned());
        }
        target.sources = parse_sources(
            &target.config,
            &target.project_root,
            std::mem::take(&mut target.sources),
            &target.project_inputs,
        )?;
        target.repository_facts = Some(python_repository_fact_payload(&target.sources));
    }
    repository_target_payloads(&plan)
}

fn fresh_structured_execution(
    options: &CheckOptions,
    mut plan: CheckPlans,
    collect_repository_facts: bool,
) -> Result<StructuredCheckExecution, String> {
    let results = evaluate_checks(&mut plan, options, collect_repository_facts)?;
    let repository_targets = if collect_repository_facts {
        repository_target_payloads(&plan)?
    } else {
        Vec::new()
    };
    let cacheable = results
        .iter()
        .all(|result| result.cacheable.unwrap_or(true));
    let mut messages: Vec<String> = Vec::new();
    let cache_stats = plan.cache_enabled.then(|| {
        if cacheable {
            CheckCacheStats {
                misses: plan.sources.len(),
                writes: plan.sources.len(),
                ..CheckCacheStats::default()
            }
        } else {
            CheckCacheStats {
                non_cacheable: plan.sources.len(),
                ..CheckCacheStats::default()
            }
        }
    });
    if plan.cache_enabled && cacheable {
        let payload = StructuredCachePayload {
            results: results.clone(),
            repository_targets: repository_targets.clone(),
        };
        let output = serde_json::to_string(&payload).map_err(|error| error.to_string())?;
        let cached = CachedOutput {
            identity: plan.identity.clone(),
            output,
            exit_code: i32::from(results.iter().any(|result| !result.faults.is_empty())),
            file_count: plan.sources.len(),
        };
        if !cache::write(&plan.root, &cached, &plan.sources, false) {
            messages.push("Cache disabled for this run: cache publication failed".to_owned());
        }
    } else if plan.cache_enabled {
        messages.push(
            "Cache disabled for this run: Rust workspace metadata was unavailable".to_owned(),
        );
    }
    Ok(StructuredCheckExecution {
        results,
        cache: cache_stats,
        messages,
        root: plan.root,
        color: plan.color,
        show_warnings: options.warn,
        repository_targets,
    })
}

fn repository_target_payloads(plan: &CheckPlans) -> Result<Vec<RepositoryTargetPayload>, String> {
    plan.plans
        .iter()
        .map(|target| {
            let name = target
                .config
                .target
                .clone()
                .ok_or_else(|| "Repository rules require explicit named targets.".to_owned())?;
            let facts = target
                .repository_facts
                .clone()
                .ok_or_else(|| format!("Repository facts were not collected for target {name}."))?;
            let subjects: Vec<CustomRuleSubject> =
                repository_subjects(&target.sources, target.config.analyzer);
            let ownership_roots = repository_ownership_roots(&target.config, &facts);
            Ok(RepositoryTargetPayload {
                name,
                analyzer: target.config.analyzer,
                root: target.config.target_root.clone(),
                ownership_roots,
                facts,
                subjects,
            })
        })
        .collect()
}

fn repository_ownership_roots(config: &Config, facts: &serde_json::Value) -> Vec<String> {
    if config.analyzer == crate::analyzer::AnalyzerId::Rust && config.ownership_roots.is_empty() {
        let mut roots = facts
            .get("files")
            .and_then(serde_json::Value::as_array)
            .into_iter()
            .flatten()
            .filter_map(|file| file.get("source_root"))
            .filter_map(serde_json::Value::as_str)
            .map(str::to_owned)
            .collect::<Vec<_>>();
        roots.sort();
        roots.dedup();
        return roots;
    }
    config
        .resolved_ownership_roots
        .iter()
        .map(|root| root.path.clone())
        .collect()
}

fn repository_subjects(
    sources: &[ScopedSource],
    analyzer: crate::analyzer::AnalyzerId,
) -> Vec<CustomRuleSubject> {
    let mut subjects: Vec<CustomRuleSubject> = Vec::new();
    for source in sources {
        let evaluated = source.purpose.is_direct()
            || analyzer == crate::analyzer::AnalyzerId::Svelte
                && source.purpose == crate::models::SourcePurpose::Support
                && web::is_direct_source(&source.path, crate::analyzer::AnalyzerId::TypeScript);
        if evaluated {
            subjects.push(CustomRuleSubject {
                path: source.target_path.clone(),
                scope: source.scope.clone(),
                scope_root: source.root_text.clone(),
                relative_parts: source.relative_parts.clone(),
                ownership_root: source.ownership_root.clone(),
                ownership_root_declaration: source.ownership_root_declaration.clone(),
                ownership_relative_parts: source.ownership_relative_parts.clone(),
            });
        }
    }
    subjects
}
