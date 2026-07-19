use std::collections::{BTreeMap, HashMap, HashSet};
use std::path::Path;

use fensu_native::rules::main::evaluate_core_rules::evaluate_core_rules;
use fensu_native::rules::main::plan_core_rule_queries::plan_core_rule_queries;
use fensu_native::rules::models::NativeRuleContext;
use rayon::iter::{IndexedParallelIterator, IntoParallelRefIterator, ParallelIterator};

use crate::constants::{
    OWNER_FILE, OWNER_PACKAGE, ROLE_HELPERS, ROLE_MAIN, SCOPE_TEST, SUFFIX_INIT,
};
use crate::helpers::check_policy::{
    apply_exceptions, is_entry_module, is_main_module, program, resolved_thresholds, role,
    scope_roots, source_module_name,
};
use crate::helpers::check_project::{observe, project_plane};
use crate::helpers::{render, rule};
use crate::models::{Config, Fault, RuleMetadata, ScopedSource};

pub(crate) fn evaluate_and_render(
    root: &Path,
    config: &Config,
    sources: &[ScopedSource],
    excluded: usize,
    show_warnings: bool,
    color: bool,
) -> Result<(String, i32), String> {
    let blocking = selected_rules(&config.select, &config.ignore);
    let warning_rules = if show_warnings {
        selected_rules(&config.warn, &config.ignore)
    } else {
        Vec::new()
    };
    let mut all_rules = blocking.clone();
    all_rules.extend(warning_rules.iter().copied());
    let codes_by_source = owner_plan(sources, &all_rules);
    let project = project_plane(root, config, sources)?;
    let program_by_path = sources
        .iter()
        .map(|source| (source.repository_path.as_str(), program(source)))
        .collect::<HashMap<_, _>>();
    let program_by_module = sources
        .iter()
        .filter(|source| source.scope != SCOPE_TEST)
        .map(|source| (source_module_name(source, root), program(source)))
        .collect::<HashMap<_, _>>();
    let warning_codes = warning_rules
        .iter()
        .map(|rule| rule.code.as_str())
        .collect::<HashSet<_>>();
    let mut uses = Vec::new();
    let batches = sources
        .par_iter()
        .zip(codes_by_source.par_iter())
        .map(|(source, codes)| {
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
                package_name: source
                    .root
                    .file_name()
                    .map(|value| value.to_string_lossy().into_owned())
                    .unwrap_or_else(|| source.root_text.clone()),
                tooling_packages: config
                    .tooling
                    .iter()
                    .filter_map(|path| Path::new(path).file_name())
                    .map(|name| name.to_string_lossy().into_owned())
                    .collect(),
                scope_roots: scope_roots(config),
                observations: HashMap::new(),
                custom_registrations: Vec::new(),
                repo_root: root.to_string_lossy().into_owned(),
            };
            let plans = plan_core_rule_queries(program(source), codes, &context);
            context.observations = observe(root, &plans, &program_by_path, &program_by_module);
            let rows = evaluate_core_rules(program(source), codes, &context, &project)?;
            let faults = rows
                .into_iter()
                .map(|row| {
                    let metadata = rule::rule(&row.code)
                        .ok_or_else(|| format!("Unknown native rule code: {}", row.code))?;
                    let path = row.path.unwrap_or_else(|| source.repository_path.clone());
                    Ok(Fault {
                        warning: warning_codes.contains(row.code.as_str()),
                        code: row.code,
                        path: root.join(path).to_string_lossy().into_owned(),
                        line: Some(row.line),
                        column: Some(row.column),
                        message: row.message.unwrap_or_else(|| metadata.message.clone()),
                        remediation: row.remediation.or_else(|| metadata.remediation.clone()),
                    })
                })
                .collect::<Result<Vec<_>, String>>()?;
            Ok((faults, source_uses))
        })
        .collect::<Result<Vec<_>, String>>()?;
    let mut faults = Vec::new();
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
    let (faults, applied) = apply_exceptions(faults, config)?;
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
    let output = render::report(render::ReportRequest {
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

pub(crate) fn selected_rules(select: &[String], ignore: &[String]) -> Vec<&'static RuleMetadata> {
    rule::catalogue()
        .iter()
        .filter(|rule| {
            let selected = select
                .iter()
                .any(|selector| rule.code.starts_with(selector));
            let explicit = select.iter().any(|selector| selector == &rule.code);
            (rule.enabled_by_default && selected || explicit)
                && !ignore
                    .iter()
                    .any(|selector| rule.code.starts_with(selector))
        })
        .collect()
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
        "subdomain" => {
            subdomain.map(|value| format!("{}\0{}\0{value}", source.scope, source.root_text))
        }
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
