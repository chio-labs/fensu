use std::collections::{BTreeMap, HashMap, HashSet};
use std::path::Path;

use fensu_facts::extension::models::ProgramHandle;
use fensu_native::rules::main::evaluate_core_rules::evaluate_core_rules;
use fensu_native::rules::main::plan_core_rule_queries::plan_core_rule_queries;
use fensu_native::rules::models::NativeRuleContext;
use rayon::iter::{IndexedParallelIterator, IntoParallelRefIterator, ParallelIterator};

use crate::catalogue::main::rule_metadata::rule_metadata;
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
use crate::check::models::EvaluationRequest;
use crate::constants::{
    OWNER_FILE, OWNER_PACKAGE, ROLE_HELPERS, ROLE_MAIN, SCOPE_TEST, SUFFIX_INIT,
};
use crate::models::{Config, Fault, RuleMetadata, ScopedSource, ThresholdUse};
use crate::reporting::main::report::report;
use crate::reporting::models::ReportRequest;

pub(crate) fn evaluate_and_render(request: EvaluationRequest<'_>) -> Result<(String, i32), String> {
    let EvaluationRequest {
        root,
        config,
        sources,
        excluded,
        show_warnings,
        color,
    } = request;
    validate_config_tiers(config)?;
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
    let codes_by_source = owner_plan(sources, &all_rules);
    let project = project_plane(root, config, sources)?;
    let program_by_path = sources
        .iter()
        .map(|source| (source.repository_path.as_str(), program(source)))
        .collect::<HashMap<_, _>>();
    let mut program_by_module: HashMap<String, &ProgramHandle> = HashMap::new();
    for source in sources.iter().filter(|source| source.scope != SCOPE_TEST) {
        program_by_module.insert(source_module_name(source, root), program(source));
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
            let (thresholds, source_uses) = resolved_thresholds(source, config, codes);
            let mut context = NativeRuleContext {
                scope: source.scope.clone(),
                role: role(source),
                is_main_module: is_main_module(source),
                thresholds,
                repository_path: source.repository_path.clone(),
                contracts: config.contracts.clone(),
                relative_parts: source.relative_parts.clone(),
                is_entry_module: is_entry_module(source),
                package_name: package_name(source),
                tooling_packages: tooling_packages(config),
                scope_roots: scope_roots(config),
                test_scopes: config.test_scopes.clone(),
                observations: HashMap::new(),
                custom_registrations: Vec::new(),
                repo_root: root.to_string_lossy().into_owned(),
                rule_options: native_rule_options(codes, config)?,
            };
            let plans = plan_core_rule_queries(program(source), &implementation_codes, &context);
            context.observations = observe(root, &plans, &program_by_path, &program_by_module);
            let rows =
                evaluate_core_rules(program(source), &implementation_codes, &context, &project)?;
            let mut faults: Vec<Fault> = Vec::new();
            for row in rows {
                let display_code = display_codes.get(&row.code).ok_or_else(|| {
                    format!("No selected identity for native rule code: {}", row.code)
                })?;
                let metadata = rule_metadata(display_code)
                    .ok_or_else(|| format!("Unknown native rule code: {display_code}"))?;
                let path = row.path.unwrap_or_else(|| source.repository_path.clone());
                faults.push(Fault {
                    warning: warning_codes.contains(display_code.as_str()),
                    code: display_code.clone(),
                    alias_of: metadata.alias_of.clone(),
                    path: root.join(path).to_string_lossy().into_owned(),
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
        root,
        evaluated_codes: &evaluated_codes,
        config,
    })?;
    let faults = apply_rule_ignores(faults, root, config);
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
    let summary = (excluded > 0).then(|| {
        format!(
            "Evaluation: {} of {} Python files ({} excluded by config)",
            sources.len(),
            sources.len() + excluded,
            excluded
        )
    });
    let output = report(ReportRequest {
        faults: &blocking_faults,
        warnings: &warnings,
        root,
        color,
        show_warnings,
        evaluation_summary: summary.as_deref(),
        applied_exceptions: applied,
        threshold_uses: &uses,
    });
    Ok((output, i32::from(!blocking_faults.is_empty())))
}

fn native_rule_options(
    codes: &[String],
    config: &Config,
) -> Result<HashMap<String, HashMap<String, String>>, String> {
    let mut by_code: HashMap<String, HashMap<String, String>> = HashMap::new();
    for code in codes {
        let rule =
            rule_metadata(code).ok_or_else(|| format!("Unknown native rule code: {code}"))?;
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
                rule_metadata(code).ok_or_else(|| format!("Unknown native rule code: {code}"))?;
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

pub(crate) fn owner_plan(sources: &[ScopedSource], rules: &[&RuleMetadata]) -> Vec<Vec<String>> {
    let mut planned = vec![Vec::new(); sources.len()];
    for rule in rules {
        let applicable = sources
            .iter()
            .enumerate()
            .filter(|(_, source)| family_applies(&rule.family, &source.scope))
            .collect::<Vec<_>>();
        if rule.execution_owner == OWNER_FILE {
            for (index, _) in applicable {
                planned[index].push(rule.code.clone());
            }
            continue;
        }
        let mut groups = BTreeMap::<String, Vec<usize>>::new();
        for (index, source) in applicable {
            if let Some(identity) = owner_identity(source, &rule.execution_owner) {
                groups.entry(identity).or_default().push(index);
            }
        }
        for indexes in groups.values() {
            if let Some(index) = indexes
                .iter()
                .min_by_key(|index| anchor_key(&sources[**index], &rule.execution_owner))
            {
                planned[*index].push(rule.code.clone());
            }
        }
    }
    planned
}

pub(crate) fn family_applies(family: &str, scope: &str) -> bool {
    if scope == SCOPE_TEST {
        matches!(family, "annotations" | "tests")
    } else {
        !matches!(family, "tests" | "custom")
    }
}

pub(crate) fn owner_identity(source: &ScopedSource, owner: &str) -> Option<String> {
    let domain = source
        .relative_parts
        .first()
        .filter(|part| !part.ends_with(".py"));
    let subdomain = source.relative_parts.get(1).filter(|part| {
        !part.ends_with(".py") && !matches!(part.as_str(), ROLE_MAIN | ROLE_HELPERS | "classes")
    });
    match owner {
        "project" => Some("project".to_owned()),
        "scope" => Some(format!("{}\0{}", source.scope, source.root_text)),
        "package" => source
            .path
            .parent()
            .map(|path| path.to_string_lossy().into_owned()),
        "domain" => domain.map(|value| format!("{}\0{}\0{value}", source.scope, source.root_text)),
        "subdomain" => subdomain.map(|value| {
            format!(
                "{}\0{}\0{}\0{value}",
                source.scope,
                source.root_text,
                domain.map(String::as_str).unwrap_or_default()
            )
        }),
        "leaf" => domain.map(|value| {
            format!(
                "{}\0{}\0{value}\0{}",
                source.scope,
                source.root_text,
                subdomain.map(String::as_str).unwrap_or_default()
            )
        }),
        _ => None,
    }
}

pub(crate) fn anchor_key(source: &ScopedSource, owner: &str) -> (bool, usize, String) {
    let init = source
        .relative_parts
        .last()
        .is_some_and(|part| part == SUFFIX_INIT);
    let expected_depth = match owner {
        "scope" => Some(1),
        "domain" => Some(2),
        "subdomain" => Some(3),
        "leaf" => Some(
            if source.relative_parts.get(1).is_some_and(|part| {
                !part.ends_with(".py")
                    && !matches!(part.as_str(), ROLE_MAIN | ROLE_HELPERS | "classes")
            }) {
                3
            } else {
                2
            },
        ),
        _ => None,
    };
    let owner_init = if owner == OWNER_PACKAGE {
        init
    } else {
        init && expected_depth == Some(source.relative_parts.len())
    };
    (
        !owner_init,
        source.relative_parts.len(),
        source.repository_path.clone(),
    )
}
