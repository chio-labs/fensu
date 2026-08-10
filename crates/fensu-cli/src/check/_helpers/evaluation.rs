use std::collections::{HashMap, HashSet};
use std::path::Path;

use fensu_facts::extension::models::ProgramHandle;
use fensu_native::rules::main::evaluate_core_rules::evaluate_core_rules;
use fensu_native::rules::main::plan_core_rule_queries::plan_core_rule_queries;
use fensu_native::rules::main::plan_execution_owners::plan_execution_owners;
use fensu_native::rules::models::{NativeExecutionRule, NativeExecutionTarget, NativeRuleContext};
use rayon::iter::{IndexedParallelIterator, IntoParallelRefIterator, ParallelIterator};

use crate::catalogue::main::rule_metadata::rule_metadata;
use crate::catalogue::models::RuleMetadata;
use crate::check::_helpers::exceptions::{apply_exceptions, ApplyExceptionsRequest};
use crate::check::_helpers::policy::{
    apply_rule_ignores, is_entry_module, is_main_module, program, role, scope_roots,
    source_module_name,
};
use crate::check::_helpers::project::{observe, project_plane};
use crate::check::_helpers::rule_policy::{
    display_codes_by_implementation, resolved_thresholds, selected_rules, validate_config_tiers,
    validate_unique_implementations,
};
use crate::check::models::{CheckResult, EvaluationRequest};
use crate::constants::SCOPE_TEST;
use crate::models::{Config, Fault, ScopedSource, ThresholdUse};
use crate::reporting::main::report::report;
use crate::reporting::models::ReportRequest;

pub(crate) fn evaluate(request: EvaluationRequest<'_>) -> Result<CheckResult, String> {
    let EvaluationRequest {
        project_root,
        config,
        sources,
        excluded,
        show_warnings,
    } = request;
    validate_config_tiers(config)?;
    if config.analyzer != crate::analyzer::AnalyzerId::Python {
        return evaluate_parser_target(config, sources, excluded, show_warnings);
    }
    let blocking = selected_rules(config, &config.select, &config.ignore)?;
    let warning_rules = if show_warnings {
        selected_rules(config, &config.warn, &config.ignore)?
    } else {
        Vec::new()
    };
    let mut all_rules = blocking.clone();
    all_rules.extend(warning_rules.iter().copied());
    validate_unique_implementations(&all_rules)?;
    let evaluated_codes = all_rules
        .iter()
        .map(|rule| rule.code.as_str())
        .collect::<HashSet<_>>();
    let codes_by_source = owner_plan(sources, &all_rules)?;
    let project = project_plane(project_root, config, sources)?;
    let program_by_path = sources
        .iter()
        .map(|source| (source.target_path.as_str(), program(source)))
        .collect::<HashMap<_, _>>();
    let mut program_by_module: HashMap<String, &ProgramHandle> = HashMap::new();
    for source in sources.iter().filter(|source| source.scope != SCOPE_TEST) {
        program_by_module.insert(source_module_name(source, project_root), program(source));
    }
    let warning_codes = warning_rules
        .iter()
        .map(|rule| rule.code.as_str())
        .collect::<HashSet<_>>();
    let mut uses: Vec<ThresholdUse> = Vec::new();
    let batches = sources
        .par_iter()
        .zip(codes_by_source.par_iter())
        .map(|(source, codes)| {
            let implementation_codes = implementation_codes(codes)?;
            let display_codes = display_codes_by_implementation(codes)?;
            let (thresholds, source_uses) = resolved_thresholds(source, config, codes)?;
            let mut context = NativeRuleContext {
                scope: source.scope.clone(),
                role: role(source),
                is_main_module: is_main_module(source),
                thresholds,
                repository_path: source.target_path.clone(),
                contracts: config.contracts.clone(),
                relative_parts: source.relative_parts.clone(),
                is_entry_module: is_entry_module(source),
                package_name: package_name(source),
                tooling_packages: tooling_packages(config),
                scope_roots: scope_roots(config),
                test_scopes: config.test_scopes.clone(),
                observations: HashMap::new(),
                custom_registrations: Vec::new(),
                repo_root: project_root.to_string_lossy().into_owned(),
                rule_options: native_rule_options(codes, config)?,
            };
            let plans = plan_core_rule_queries(program(source), &implementation_codes, &context);
            context.observations =
                observe(project_root, &plans, &program_by_path, &program_by_module)?;
            let rows =
                evaluate_core_rules(program(source), &implementation_codes, &context, &project)?;
            let mut faults: Vec<Fault> = Vec::new();
            for row in rows {
                let display_code = display_codes.get(&row.code).ok_or_else(|| {
                    format!("No selected identity for native rule code: {}", row.code)
                })?;
                let metadata = rule_metadata(display_code)?
                    .ok_or_else(|| format!("Unknown native rule code: {display_code}"))?;
                let path = row.path.unwrap_or_else(|| source.target_path.clone());
                faults.push(Fault {
                    warning: warning_codes.contains(display_code.as_str()),
                    code: display_code.clone(),
                    alias_of: metadata.alias_of.clone(),
                    path: project_root.join(path).to_string_lossy().into_owned(),
                    line: Some(row.line),
                    column: Some(row.column),
                    message: row.message.unwrap_or_else(|| metadata.message.clone()),
                    remediation: row.remediation.or_else(|| metadata.remediation.clone()),
                });
            }
            Ok((faults, source_uses))
        })
        .collect::<Result<Vec<_>, String>>()?;
    let mut faults: Vec<Fault> = Vec::new();
    for (batch, batch_uses) in batches {
        faults.extend(batch);
        uses.extend(batch_uses);
    }
    faults.sort_by(|left, right| {
        (
            &left.path,
            left.line.unwrap_or(0),
            left.column.unwrap_or(0),
            &left.code,
        )
            .cmp(&(
                &right.path,
                right.line.unwrap_or(0),
                right.column.unwrap_or(0),
                &right.code,
            ))
    });
    uses.sort();
    uses.dedup();
    let (faults, applied) = apply_exceptions(ApplyExceptionsRequest {
        faults,
        sources,
        project_root,
        evaluated_codes: &evaluated_codes,
        config,
    })?;
    let faults = apply_rule_ignores(faults, project_root, config);
    let blocking_faults = faults
        .iter()
        .filter(|fault| !fault.warning)
        .cloned()
        .collect::<Vec<_>>();
    let warnings = faults
        .iter()
        .filter(|fault| fault.warning)
        .cloned()
        .collect::<Vec<_>>();
    Ok(CheckResult {
        analyzer: config.analyzer,
        faults: blocking_faults,
        warnings,
        selected: sources.len(),
        excluded,
        applied_exceptions: applied,
        threshold_uses: uses,
    })
}

fn evaluate_parser_target(
    config: &Config,
    sources: &[ScopedSource],
    excluded: usize,
    show_warnings: bool,
) -> Result<CheckResult, String> {
    if !config.rule_paths.is_empty()
        || !config.rule_modules.is_empty()
        || !config.rule_options.is_empty()
    {
        return Err(format!(
            "Native {} check integration does not support Python-hosted rule paths, modules, or options.",
            config.analyzer
        ));
    }
    let blocking = selected_rules(config, &config.select, &config.ignore)?;
    let warnings = if show_warnings {
        selected_rules(config, &config.warn, &config.ignore)?
    } else {
        Vec::new()
    };
    if !blocking.is_empty() || !warnings.is_empty() {
        return Err(format!(
            "Native {} policy evaluation is not available; only the internal parser gate is active.",
            config.analyzer
        ));
    }
    if config
        .exceptions
        .iter()
        .any(|entry| !entry.symbols.is_empty())
    {
        return Err(format!(
            "Symbol-scoped rule exceptions are unsupported for analyzer {}; owner resolution is unavailable.",
            config.analyzer
        ));
    }
    Ok(CheckResult {
        analyzer: config.analyzer,
        faults: Vec::new(),
        warnings: Vec::new(),
        selected: sources.iter().filter(|source| source.direct).count(),
        excluded,
        applied_exceptions: 0,
        threshold_uses: Vec::new(),
    })
}

pub(crate) fn render_results(
    mut results: Vec<CheckResult>,
    root: &Path,
    color: bool,
    show_warnings: bool,
) -> (String, i32) {
    let selected = results.iter().map(|result| result.selected).sum::<usize>();
    let excluded = results.iter().map(|result| result.excluded).sum::<usize>();
    let applied_exceptions = results
        .iter()
        .map(|result| result.applied_exceptions)
        .sum::<usize>();
    let python_only = results
        .iter()
        .all(|result| result.analyzer == crate::analyzer::AnalyzerId::Python);
    let mut faults = results
        .iter_mut()
        .flat_map(|result| std::mem::take(&mut result.faults))
        .collect::<Vec<_>>();
    let mut warnings = results
        .iter_mut()
        .flat_map(|result| std::mem::take(&mut result.warnings))
        .collect::<Vec<_>>();
    let mut threshold_uses = results
        .iter_mut()
        .flat_map(|result| std::mem::take(&mut result.threshold_uses))
        .collect::<Vec<_>>();
    let fault_order = |left: &Fault, right: &Fault| {
        (
            &left.path,
            left.line.unwrap_or(0),
            left.column.unwrap_or(0),
            &left.code,
        )
            .cmp(&(
                &right.path,
                right.line.unwrap_or(0),
                right.column.unwrap_or(0),
                &right.code,
            ))
    };
    faults.sort_by(fault_order);
    warnings.sort_by(fault_order);
    threshold_uses.sort();
    threshold_uses.dedup();
    let summary = (excluded > 0).then(|| {
        if python_only {
            format!(
                "Evaluation: {selected} of {} Python files ({excluded} excluded by config)",
                selected + excluded
            )
        } else {
            format!(
                "Evaluation: {selected} of {} source files ({excluded} excluded by config)",
                selected + excluded
            )
        }
    });
    let output = report(ReportRequest {
        faults: &faults,
        warnings: &warnings,
        root,
        color,
        show_warnings,
        evaluation_summary: summary.as_deref(),
        applied_exceptions,
        threshold_uses: &threshold_uses,
    });
    (output, i32::from(!faults.is_empty()))
}

fn native_rule_options(
    codes: &[String],
    config: &Config,
) -> Result<HashMap<String, HashMap<String, String>>, String> {
    let mut by_code: HashMap<String, HashMap<String, String>> = HashMap::new();
    for code in codes {
        let rule =
            rule_metadata(code)?.ok_or_else(|| format!("Unknown native rule code: {code}"))?;
        let mut values: HashMap<String, String> = HashMap::new();
        for option in &rule.options {
            let configured = config
                .rule_options
                .get(code)
                .and_then(toml::Value::as_table)
                .and_then(|table| table.get(&option.name));
            values.insert(
                option.name.clone(),
                match configured {
                    Some(value) => {
                        serde_json::to_string(value).map_err(|error| error.to_string())?
                    }
                    None => serde_json::to_string(&option.current_value)
                        .map_err(|error| error.to_string())?,
                },
            );
        }
        if !values.is_empty() {
            by_code.insert(
                rule.alias_of.clone().unwrap_or_else(|| rule.code.clone()),
                values,
            );
        }
    }
    Ok(by_code)
}

fn implementation_codes(codes: &[String]) -> Result<Vec<String>, String> {
    codes
        .iter()
        .map(|code| {
            let metadata =
                rule_metadata(code)?.ok_or_else(|| format!("Unknown native rule code: {code}"))?;
            Ok(metadata.alias_of.clone().unwrap_or_else(|| code.clone()))
        })
        .collect()
}

fn tooling_packages(config: &Config) -> Vec<String> {
    let mut packages: Vec<String> = Vec::new();
    for path in &config.tooling {
        if let Some(name) = Path::new(path).file_name() {
            packages.push(name.to_string_lossy().into_owned());
        }
    }
    packages
}

fn package_name(source: &ScopedSource) -> String {
    source
        .root
        .file_name()
        .map(|value| value.to_string_lossy().into_owned())
        .unwrap_or_else(|| source.root_text.clone())
}

pub(crate) fn owner_plan(
    sources: &[ScopedSource],
    rules: &[&RuleMetadata],
) -> Result<Vec<Vec<String>>, String> {
    let targets: Vec<NativeExecutionTarget> = sources
        .iter()
        .map(|source| NativeExecutionTarget {
            repository_path: source.target_path.clone(),
            scope: source.scope.clone(),
            root: source.root_text.clone(),
            relative_parts: source.relative_parts.clone(),
            direct: true,
        })
        .collect();
    let native_rules: Vec<NativeExecutionRule> = rules
        .iter()
        .map(|rule| {
            NativeExecutionRule::new(
                rule.code.clone(),
                rule.family.clone(),
                rule.execution_owner.clone(),
            )
        })
        .collect();
    Ok(plan_execution_owners(&targets, &native_rules)?
        .into_iter()
        .map(|plan| plan.codes)
        .collect())
}
