use std::collections::{HashMap, HashSet};
use std::path::Path;

use fensu_facts::extension::models::ProgramHandle;
use fensu_native::rules::main::evaluate_core_rules::evaluate_core_rules;
use fensu_native::rules::main::plan_core_rule_queries::plan_core_rule_queries;
use fensu_native::rules::main::plan_execution_owners::plan_execution_owners;
use fensu_native::rules::models::{NativeExecutionRule, NativeExecutionTarget, NativeRuleContext};
use fensu_policy::lifecycle::models::FindingSeverity;
use rayon::iter::{IndexedParallelIterator, IntoParallelRefIterator, ParallelIterator};

use crate::catalogue::main::rule_catalogue::configured_rule_catalogue;
use crate::catalogue::main::rule_metadata::rule_metadata;
use crate::catalogue::models::RuleMetadata;
use crate::check::_helpers::exceptions::{apply_exceptions, ApplyExceptionsRequest};
use crate::check::_helpers::policy::{
    apply_rule_ignores, is_entry_module, is_main_module, program, role, scope_roots,
    source_module_name,
};
use crate::check::_helpers::project::{observe, project_plane};
use crate::check::_helpers::rule_policy::{
    applicable, display_codes_by_implementation, resolved_thresholds, selected_rules,
    validate_config_tiers, validate_unique_implementations,
};
use crate::check::models::WebCustomRulePayload;
use crate::check::models::{CheckResult, EvaluationRequest, TargetEvaluation};
use crate::check::models::{CustomRuleSubject, RustCustomRulePayload};
use crate::check::repository_custom_facts::python_repository_fact_payload;
use crate::check::web_custom_facts::web_fact_payload;
use crate::check::web_policy::{self, WebPolicyRequest};
use crate::constants::{
    CUSTOM_RULE_TEST_COVERAGE_CODE, PROJECT_RULE_REQUESTER, RUST_CUSTOM_DEPENDENCY_KINDS,
    SCOPE_TEST, WEB_CUSTOM_DEPENDENCY_KINDS, WEB_PARSE_DIAGNOSTIC_CODE,
};
use crate::hosting::main::run_rust_custom_rule_host::run_rust_custom_rule_host;
use crate::hosting::main::run_web_custom_rule_host::run_web_custom_rule_host;
use crate::models::{Config, Fault, ScopedSource, ThresholdUse};
use crate::reporting::main::report::report;
use crate::reporting::models::ReportRequest;

pub(crate) fn evaluate(request: EvaluationRequest<'_>) -> Result<TargetEvaluation, String> {
    let EvaluationRequest {
        project_root,
        config,
        sources,
        project_inputs,
        excluded,
        show_warnings,
        cache_enabled,
        collect_repository_facts,
    } = request;
    validate_config_tiers(config)?;
    if config.analyzer == crate::analyzer::AnalyzerId::Rust {
        return evaluate_rust_target(EvaluationRequest {
            project_root,
            config,
            sources,
            project_inputs,
            excluded,
            show_warnings,
            cache_enabled,
            collect_repository_facts,
        });
    }
    if config.analyzer != crate::analyzer::AnalyzerId::Python {
        return evaluate_parser_target(EvaluationRequest {
            project_root,
            config,
            sources,
            project_inputs,
            excluded,
            show_warnings,
            cache_enabled,
            collect_repository_facts,
        });
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
    Ok(TargetEvaluation {
        result: CheckResult {
            analyzer: config.analyzer,
            faults: blocking_faults,
            warnings,
            selected: sources.len(),
            excluded,
            applied_exceptions: applied,
            threshold_uses: uses,
            cacheable: Some(true),
        },
        repository_facts: collect_repository_facts.then(|| python_repository_fact_payload(sources)),
    })
}

fn evaluate_rust_target(request: EvaluationRequest<'_>) -> Result<TargetEvaluation, String> {
    let EvaluationRequest {
        project_root,
        config,
        sources,
        project_inputs: _,
        excluded,
        show_warnings,
        cache_enabled,
        collect_repository_facts,
    } = request;
    let custom_option_codes = config
        .rule_options
        .keys()
        .filter(|code| code.starts_with('X'))
        .collect::<Vec<_>>();
    let custom_selected = rust_custom_rules_selected(config, show_warnings);
    if !custom_option_codes.is_empty() && !custom_selected {
        return Err(format!(
            "Rust custom rule options require a selected custom rule: {}.",
            custom_option_codes
                .iter()
                .map(|code| code.as_str())
                .collect::<Vec<_>>()
                .join(", ")
        ));
    }
    let native_select = config
        .select
        .iter()
        .filter(|selector| !selector.starts_with('X'))
        .cloned()
        .collect::<Vec<_>>();
    let native_warn = config
        .warn
        .iter()
        .filter(|selector| !selector.starts_with('X'))
        .cloned()
        .collect::<Vec<_>>();
    let native_ignore = config
        .ignore
        .iter()
        .filter(|selector| !selector.starts_with('X'))
        .cloned()
        .collect::<Vec<_>>();
    let blocking = selected_rules(config, &native_select, &native_ignore)?;
    let warning_rules = if show_warnings {
        selected_rules(config, &native_warn, &native_ignore)?
    } else {
        Vec::new()
    };
    let mut all_rules = blocking.clone();
    all_rules.extend(warning_rules.iter().copied());
    let custom_host_required = custom_rules_configured(config)
        && (custom_selected
            || all_rules
                .iter()
                .any(|rule| rule.code == CUSTOM_RULE_TEST_COVERAGE_CODE));
    validate_unique_implementations(&all_rules)?;
    let warning_codes = warning_rules
        .iter()
        .map(|rule| rule.code.as_str())
        .collect::<HashSet<_>>();
    let display_by_implementation = all_rules
        .iter()
        .map(|rule| {
            (
                rule.implementation_code.as_deref().unwrap_or(&rule.code),
                *rule,
            )
        })
        .collect::<HashMap<_, _>>();
    let native_options = config
        .rule_options
        .iter()
        .filter(|(code, _)| !code.starts_with('X'))
        .map(|(code, options)| (code.clone(), options.clone()))
        .collect::<toml::map::Map<_, _>>();
    let analysis = fensu_rust::engine::main::analyze_repository::analyze_repository(
        project_root,
        Some(&native_options),
        &config.tooling,
    )?;
    let repository_facts: Option<serde_json::Value> = collect_repository_facts
        .then(|| serde_json::to_value(&analysis.facts).map_err(|error| error.to_string()))
        .transpose()?;
    let mut cacheable = !analysis
        .diagnostics
        .iter()
        .any(|diagnostic| diagnostic.code == fensu_rust::METADATA_SETUP_CODE);
    let excluded_paths = sources
        .iter()
        .filter(|source| !source.purpose.is_direct())
        .map(|source| source.target_path.as_str())
        .collect::<HashSet<_>>();
    let source_paths = sources
        .iter()
        .map(|source| source.target_path.as_str())
        .collect::<HashSet<_>>();
    let mut faults: Vec<Fault> = Vec::new();
    for diagnostic in analysis.diagnostics {
        let diagnostic_path = diagnostic.path.to_string_lossy().replace('\\', "/");
        if excluded_paths.contains(diagnostic_path.as_str()) {
            continue;
        }
        if diagnostic_path.ends_with(".rs") && !source_paths.contains(diagnostic_path.as_str()) {
            continue;
        }
        let Some(metadata) = display_by_implementation.get(diagnostic.code) else {
            continue;
        };
        let line = diagnostic
            .line
            .map(u32::try_from)
            .transpose()
            .map_err(|_| "Rust diagnostic line exceeds the supported range.".to_owned())?;
        faults.push(Fault {
            warning: warning_codes.contains(metadata.code.as_str()),
            code: metadata.code.clone(),
            alias_of: None,
            path: project_root
                .join(diagnostic_path)
                .to_string_lossy()
                .into_owned(),
            line,
            column: None,
            message: diagnostic.message,
            remediation: Some(diagnostic.remediation),
        });
    }
    let mut custom_codes: Vec<String> = Vec::new();
    if custom_host_required {
        let subjects: Vec<CustomRuleSubject> = sources
            .iter()
            .filter(|source| source.purpose.is_direct())
            .map(|source| CustomRuleSubject {
                path: source.target_path.clone(),
                scope: source.scope.clone(),
                scope_root: source.root_text.clone(),
                relative_parts: source.relative_parts.clone(),
            })
            .collect();
        let custom = run_rust_custom_rule_host(RustCustomRulePayload {
            target: config.target.clone(),
            show_warnings,
            cache_enabled,
            facts: analysis.facts,
            subjects,
        })?;
        validate_rust_custom_response(&custom, &source_paths)?;
        cacheable &= custom.cacheable;
        custom_codes.extend(custom.blocking_codes);
        custom_codes.extend(custom.warning_codes);
        for finding in custom.findings {
            if excluded_paths.contains(finding.path.as_str())
                || finding.path.ends_with(".rs") && !source_paths.contains(finding.path.as_str())
            {
                continue;
            }
            faults.push(Fault {
                warning: finding.severity == FindingSeverity::Warning,
                code: finding.code,
                alias_of: None,
                path: project_root
                    .join(finding.path)
                    .to_string_lossy()
                    .into_owned(),
                line: finding.line,
                column: finding.column,
                message: finding.message,
                remediation: finding.remediation,
            });
        }
    }
    let mut evaluated_code_values = all_rules
        .iter()
        .map(|rule| rule.code.clone())
        .collect::<Vec<_>>();
    evaluated_code_values.extend(custom_codes);
    let evaluated_codes = evaluated_code_values
        .iter()
        .map(String::as_str)
        .collect::<HashSet<_>>();
    let (faults, applied) = apply_exceptions(ApplyExceptionsRequest {
        faults,
        sources,
        project_root,
        evaluated_codes: &evaluated_codes,
        config,
    })?;
    let faults = apply_rule_ignores(faults, project_root, config);
    let (blocking_faults, warnings) = faults.into_iter().partition(|fault| !fault.warning);
    Ok(TargetEvaluation {
        result: CheckResult {
            analyzer: config.analyzer,
            faults: blocking_faults,
            warnings,
            selected: sources
                .iter()
                .filter(|source| source.purpose.is_direct())
                .count(),
            excluded,
            applied_exceptions: applied,
            threshold_uses: Vec::new(),
            cacheable: Some(cacheable),
        },
        repository_facts,
    })
}

fn rust_custom_rules_selected(config: &Config, show_warnings: bool) -> bool {
    let configured = !config.rule_paths.is_empty() || !config.rule_modules.is_empty();
    configured
        && (config
            .select
            .iter()
            .any(|selector| custom_selector_not_ignored(selector, &config.ignore))
            || show_warnings
                && config
                    .warn
                    .iter()
                    .any(|selector| custom_selector_not_ignored(selector, &config.ignore)))
}

fn custom_selector_not_ignored(selector: &str, ignores: &[String]) -> bool {
    selector.starts_with('X')
        && !ignores
            .iter()
            .any(|ignored| ignored.starts_with('X') && selector.starts_with(ignored))
}

fn custom_rules_configured(config: &Config) -> bool {
    !config.rule_paths.is_empty() || !config.rule_modules.is_empty()
}

fn validate_rust_custom_response(
    response: &crate::check::models::RustCustomRuleResponse,
    source_paths: &HashSet<&str>,
) -> Result<(), String> {
    let blocking = response
        .blocking_codes
        .iter()
        .map(String::as_str)
        .collect::<HashSet<_>>();
    let warnings = response
        .warning_codes
        .iter()
        .map(String::as_str)
        .collect::<HashSet<_>>();
    if blocking.len() != response.blocking_codes.len()
        || warnings.len() != response.warning_codes.len()
        || !blocking.is_disjoint(&warnings)
    {
        return Err(
            "Rust custom-rule host returned duplicate or overlapping rule tiers.".to_owned(),
        );
    }
    for dependency in &response.dependencies {
        if dependency.requester != PROJECT_RULE_REQUESTER
            && !source_paths.contains(dependency.requester.as_str())
            || !RUST_CUSTOM_DEPENDENCY_KINDS.contains(&dependency.kind.as_str())
            || dependency.query.is_empty()
        {
            return Err("Rust custom-rule host returned invalid dependency evidence.".to_owned());
        }
    }
    for finding in &response.findings {
        let selected = match finding.severity {
            FindingSeverity::Blocking => blocking.contains(finding.code.as_str()),
            FindingSeverity::Warning => warnings.contains(finding.code.as_str()),
        };
        if !selected
            || !(finding.code.starts_with('X') || finding.code == CUSTOM_RULE_TEST_COVERAGE_CODE)
        {
            return Err(format!(
                "Rust custom-rule host returned a finding for unselected code {}.",
                finding.code
            ));
        }
        if !confined_rust_custom_path(&finding.path) {
            return Err(format!(
                "Rust custom-rule host returned an invalid project path: {}.",
                finding.path
            ));
        }
    }
    Ok(())
}

fn confined_rust_custom_path(value: &str) -> bool {
    let path = Path::new(value);
    !value.is_empty()
        && !value.contains('\\')
        && !path.is_absolute()
        && path.components().all(|component| {
            matches!(component, std::path::Component::Normal(_))
                && !component.as_os_str().to_string_lossy().ends_with(':')
        })
}

fn evaluate_parser_target(request: EvaluationRequest<'_>) -> Result<TargetEvaluation, String> {
    let EvaluationRequest {
        project_root,
        config,
        sources,
        project_inputs,
        excluded,
        show_warnings,
        cache_enabled,
        collect_repository_facts,
    } = request;
    let custom_option_codes = config
        .rule_options
        .keys()
        .filter(|code| code.starts_with('X'))
        .collect::<Vec<_>>();
    if !custom_option_codes.is_empty() && !web_custom_rules_selected(config, show_warnings) {
        return Err(format!(
            "Web custom rule options require a selected custom rule: {}.",
            custom_option_codes
                .iter()
                .map(|code| code.as_str())
                .collect::<Vec<_>>()
                .join(", ")
        ));
    }
    let native_select = config
        .select
        .iter()
        .filter(|selector| !selector.starts_with('X'))
        .cloned()
        .collect::<Vec<_>>();
    let native_warn = config
        .warn
        .iter()
        .filter(|selector| !selector.starts_with('X'))
        .cloned()
        .collect::<Vec<_>>();
    let native_ignore = config
        .ignore
        .iter()
        .filter(|selector| !selector.starts_with('X'))
        .cloned()
        .collect::<Vec<_>>();
    let blocking = selected_rules(config, &native_select, &native_ignore)?;
    let warning_rules = if show_warnings {
        selected_rules(config, &native_warn, &native_ignore)?
    } else {
        Vec::new()
    };
    let mut all_rules = blocking.clone();
    all_rules.extend(warning_rules.iter().copied());
    validate_unique_implementations(&all_rules)?;
    let display_codes = web_display_codes(config, &all_rules)?;
    let selected_codes = all_rules
        .iter()
        .map(|rule| {
            rule.implementation_code
                .as_deref()
                .unwrap_or(rule.code.as_str())
        })
        .collect::<HashSet<_>>();
    let warning_codes = warning_rules
        .iter()
        .map(|rule| rule.code.as_str())
        .collect::<HashSet<_>>();
    let code_values = all_rules
        .iter()
        .map(|rule| rule.code.clone())
        .collect::<Vec<_>>();
    let mut threshold_values: HashMap<(String, String), u32> = HashMap::new();
    let mut uses: Vec<ThresholdUse> = Vec::new();
    for source in sources {
        let (values, source_uses) = resolved_thresholds(source, config, &code_values)?;
        for (name, value) in values {
            threshold_values.insert((source.target_path.clone(), name), value);
        }
        uses.extend(source_uses);
    }
    let rows = web_policy::evaluate(WebPolicyRequest {
        config,
        sources,
        project_inputs,
        selected_codes: &selected_codes,
        thresholds: &threshold_values,
    });
    let mut faults: Vec<Fault> = Vec::with_capacity(rows.len());
    for row in rows {
        let Some(metadata) = display_codes.get(row.code) else {
            if row.code == WEB_PARSE_DIAGNOSTIC_CODE {
                continue;
            }
            return Err(format!(
                "No configured identity for native web rule code: {}",
                row.code
            ));
        };
        faults.push(Fault {
            warning: warning_codes.contains(metadata.code.as_str()),
            code: metadata.code.clone(),
            alias_of: metadata.alias_of.clone(),
            path: project_root.join(row.path).to_string_lossy().into_owned(),
            line: row.line,
            column: row.column,
            message: row.message,
            remediation: metadata.remediation.clone(),
        });
    }
    let custom_selected = web_custom_rules_selected(config, show_warnings);
    let custom_host_required = custom_rules_configured(config)
        && (custom_selected
            || all_rules
                .iter()
                .any(|rule| rule.code == CUSTOM_RULE_TEST_COVERAGE_CODE));
    let fact_payload = (collect_repository_facts || custom_host_required)
        .then(|| web_fact_payload(config.analyzer, sources));
    let mut custom_codes: Vec<String> = Vec::new();
    let mut cacheable = true;
    if custom_host_required {
        let subject_sources = sources
            .iter()
            .filter(|source| web_custom_subject(source, config.analyzer))
            .collect::<Vec<_>>();
        let subjects: Vec<CustomRuleSubject> = subject_sources
            .iter()
            .map(|source| CustomRuleSubject {
                path: source.target_path.clone(),
                scope: source.scope.clone(),
                scope_root: source.root_text.clone(),
                relative_parts: source.relative_parts.clone(),
            })
            .collect();
        let custom = run_web_custom_rule_host(WebCustomRulePayload {
            target: config.target.clone(),
            show_warnings,
            cache_enabled,
            facts: fact_payload
                .clone()
                .ok_or_else(|| "Web custom facts were not collected.".to_owned())?,
            subjects,
        })?;
        let source_paths = sources
            .iter()
            .map(|source| source.target_path.as_str())
            .collect::<HashSet<_>>();
        validate_web_custom_response(&custom, &source_paths)?;
        cacheable &= custom.cacheable;
        custom_codes.extend(custom.blocking_codes);
        custom_codes.extend(custom.warning_codes);
        for finding in custom.findings {
            faults.push(Fault {
                warning: finding.severity == FindingSeverity::Warning,
                code: finding.code,
                alias_of: None,
                path: project_root
                    .join(finding.path)
                    .to_string_lossy()
                    .into_owned(),
                line: finding.line,
                column: finding.column,
                message: finding.message,
                remediation: finding.remediation,
            });
        }
    }
    let mut evaluated_code_values = selected_codes
        .into_iter()
        .map(str::to_owned)
        .collect::<Vec<_>>();
    evaluated_code_values.extend(custom_codes);
    let evaluated_codes = evaluated_code_values
        .iter()
        .map(String::as_str)
        .collect::<HashSet<_>>();
    let (faults, applied) = apply_exceptions(ApplyExceptionsRequest {
        faults,
        sources,
        project_root,
        evaluated_codes: &evaluated_codes,
        config,
    })?;
    let faults = apply_rule_ignores(faults, project_root, config);
    let blocking_faults: Vec<Fault> = faults
        .iter()
        .filter(|fault| !fault.warning)
        .cloned()
        .collect();
    let warnings: Vec<Fault> = faults
        .iter()
        .filter(|fault| fault.warning)
        .cloned()
        .collect();
    uses.sort();
    uses.dedup();
    Ok(TargetEvaluation {
        result: CheckResult {
            analyzer: config.analyzer,
            faults: blocking_faults,
            warnings,
            selected: sources
                .iter()
                .filter(|source| {
                    source.purpose.is_direct()
                        || config.analyzer == crate::analyzer::AnalyzerId::Svelte
                            && source.purpose == crate::models::SourcePurpose::Support
                            && crate::check::_helpers::project::is_direct_source(
                                &source.path,
                                crate::analyzer::AnalyzerId::TypeScript,
                            )
                })
                .count(),
            excluded,
            applied_exceptions: applied,
            threshold_uses: uses,
            cacheable: Some(cacheable),
        },
        repository_facts: if collect_repository_facts {
            fact_payload
        } else {
            None
        },
    })
}

fn web_custom_rules_selected(config: &Config, show_warnings: bool) -> bool {
    let configured = !config.rule_paths.is_empty() || !config.rule_modules.is_empty();
    configured
        && (config
            .select
            .iter()
            .any(|selector| custom_selector_not_ignored(selector, &config.ignore))
            || show_warnings
                && config
                    .warn
                    .iter()
                    .any(|selector| custom_selector_not_ignored(selector, &config.ignore)))
}

fn web_custom_subject(source: &ScopedSource, analyzer: crate::analyzer::AnalyzerId) -> bool {
    source.purpose.is_direct()
        || analyzer == crate::analyzer::AnalyzerId::Svelte
            && source.purpose == crate::models::SourcePurpose::Support
            && crate::check::_helpers::project::is_direct_source(
                &source.path,
                crate::analyzer::AnalyzerId::TypeScript,
            )
}

fn validate_web_custom_response(
    response: &crate::check::models::WebCustomRuleResponse,
    source_paths: &HashSet<&str>,
) -> Result<(), String> {
    let blocking = response
        .blocking_codes
        .iter()
        .map(String::as_str)
        .collect::<HashSet<_>>();
    let warnings = response
        .warning_codes
        .iter()
        .map(String::as_str)
        .collect::<HashSet<_>>();
    if blocking.len() != response.blocking_codes.len()
        || warnings.len() != response.warning_codes.len()
        || !blocking.is_disjoint(&warnings)
    {
        return Err(
            "Web custom-rule host returned duplicate or overlapping rule tiers.".to_owned(),
        );
    }
    for dependency in &response.dependencies {
        if dependency.requester != PROJECT_RULE_REQUESTER
            && !source_paths.contains(dependency.requester.as_str())
            || !WEB_CUSTOM_DEPENDENCY_KINDS.contains(&dependency.kind.as_str())
            || dependency.query.is_empty()
        {
            return Err("Web custom-rule host returned invalid dependency evidence.".to_owned());
        }
    }
    for finding in &response.findings {
        let selected = match finding.severity {
            FindingSeverity::Blocking => blocking.contains(finding.code.as_str()),
            FindingSeverity::Warning => warnings.contains(finding.code.as_str()),
        };
        if !selected
            || !(finding.code.starts_with('X') || finding.code == CUSTOM_RULE_TEST_COVERAGE_CODE)
        {
            return Err(format!(
                "Web custom-rule host returned a finding for unselected code {}.",
                finding.code
            ));
        }
        if !confined_rust_custom_path(&finding.path) {
            return Err(format!(
                "Web custom-rule host returned an invalid project path: {}.",
                finding.path
            ));
        }
    }
    Ok(())
}

fn web_display_codes(
    config: &Config,
    selected: &[&'static RuleMetadata],
) -> Result<HashMap<&'static str, &'static RuleMetadata>, String> {
    let mut display: HashMap<&'static str, &'static RuleMetadata> = HashMap::new();
    for rule in configured_rule_catalogue(&config.rule_packs)?
        .into_iter()
        .filter(|rule| applicable(rule, config))
        .filter(|rule| rule.implementation_code.is_some())
    {
        let implementation = rule.implementation_code.as_deref().unwrap_or_default();
        let preferred = rule.pack.as_deref() == Some("sveltekit");
        if preferred || !display.contains_key(implementation) {
            display.insert(implementation, rule);
        }
    }
    for rule in selected {
        if let Some(implementation) = rule.implementation_code.as_deref() {
            display.insert(implementation, *rule);
        }
    }
    Ok(display)
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
