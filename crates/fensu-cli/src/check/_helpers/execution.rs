//! Read cached results and render a fresh check run.

use fensu_facts::extension::models::ProgramHandle;

use crate::check::_helpers::cache;
use crate::check::_helpers::evaluation::evaluate_and_render;
use crate::check::_helpers::policy::python_version;
use crate::check::models::{CheckPlan, EvaluationRequest};
use crate::models::{CachedOutput, CheckOptions, CliOutput, ScopedSource};
use crate::skills::main::core_freshness;

pub(crate) fn cached_output(plan: &CheckPlan, options: &CheckOptions) -> Option<CliOutput> {
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
    stderr.push_str(
        &core_freshness::core_freshness(&plan.invocation, plan.config.target.as_deref())
            .unwrap_or_default(),
    );
    Some(CliOutput {
        stdout: cached.output,
        stderr,
        exit_code: cached.exit_code,
    })
}

pub(crate) fn render_check(
    mut plan: CheckPlan,
    options: &CheckOptions,
) -> Result<CliOutput, String> {
    parse_sources(&mut plan.sources)?;
    let (output, exit_code) = evaluate_and_render(EvaluationRequest {
        root: &plan.root,
        config: &plan.config,
        sources: &plan.sources,
        excluded: plan.excluded,
        show_warnings: options.warn,
        color: plan.color,
    })?;
    let mut stderr = String::new();
    stderr.push_str(
        &core_freshness::core_freshness(&plan.invocation, plan.config.target.as_deref())
            .unwrap_or_default(),
    );
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

fn stored_output(plan: &CheckPlan, output: &str, exit_code: i32, cache_stats: bool) -> String {
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

fn parse_sources(sources: &mut [ScopedSource]) -> Result<(), String> {
    let parsed = ProgramHandle::parse_many(
        sources
            .iter()
            .map(|source| String::from_utf8_lossy(&source.content).into_owned())
            .collect(),
        python_version(),
    );
    for (source, program) in sources.iter_mut().zip(parsed) {
        source.program =
            Some(program.ok_or_else(|| {
                format!("Could not parse Python source: {}", source.repository_path)
            })?);
    }
    Ok(())
}
