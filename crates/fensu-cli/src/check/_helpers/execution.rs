//! Read cached results and render a fresh check run.

use fensu_facts::extension::models::ProgramHandle;

use crate::check::_helpers::cache;
use crate::check::_helpers::evaluation::{evaluate, render_results};
use crate::check::_helpers::policy::python_version;
use crate::check::_helpers::project as web;
use crate::check::models::{CheckPlans, EvaluationRequest};
use crate::models::{CachedOutput, CheckOptions, CliOutput, ParsedProgram, ScopedSource};
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
    let mut results = Vec::with_capacity(plan.plans.len());
    for target in &mut plan.plans {
        target.sources = parse_sources(
            &target.config,
            &target.project_root,
            std::mem::take(&mut target.sources),
            &target.project_inputs,
        )?;
        results.push(evaluate(EvaluationRequest {
            project_root: &target.project_root,
            config: &target.config,
            sources: &target.sources,
            excluded: target.excluded,
            show_warnings: options.warn,
        })?);
    }
    let (output, exit_code) = render_results(results, &plan.root, plan.color, options.warn);
    let mut stderr = String::new();
    stderr.push_str(&freshness(&plan));
    if plan.cache_enabled {
        stderr.push_str(&stored_output(
            &plan,
            &output,
            exit_code,
            options.cache_stats,
        ));
    }
    Ok(CliOutput {
        stdout: output,
        stderr,
        exit_code,
    })
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
    let mut messages: Vec<String> = Vec::new();
    for target in &plan.plans {
        let message =
            core_freshness::core_freshness(&plan.invocation, target.config.target.as_deref())
                .unwrap_or_default();
        if !message.is_empty() && !messages.contains(&message) {
            messages.push(message);
        }
    }
    messages.concat()
}

fn parse_sources(
    config: &crate::models::Config,
    project_root: &std::path::Path,
    mut sources: Vec<ScopedSource>,
    project_inputs: &[crate::models::ProjectInput],
) -> Result<Vec<ScopedSource>, String> {
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
