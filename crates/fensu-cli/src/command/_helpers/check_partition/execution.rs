//! Partition mixed custom-Python and native-web aggregate checks.

use std::collections::HashSet;
use std::path::Path;
use std::path::PathBuf;

use fensu_policy::lifecycle::models::FindingSeverity;

use crate::analyzer::AnalyzerId;
use crate::check::main::check_output_options::check_output_options;
use crate::check::main::execute_structured_check::execute_structured_check;
use crate::check::main::render_check_results::render_check_results;
use crate::check::main::repository_python_targets::repository_python_targets;
use crate::check::models::{
    CheckCacheStats, CheckResult, RepositoryCustomRulePayload, RepositoryCustomRuleResponse,
    RepositoryTargetPayload,
};
use crate::constants::{
    CHECK_CACHE_ARGUMENT, CHECK_NO_CACHE_ARGUMENT, CHECK_WARN_ARGUMENT, PROJECT_ROOT_PATH,
    REPOSITORY_CUSTOM_DEPENDENCY_KINDS, REPOSITORY_RULE_REQUESTER,
};
use crate::hosting::main::run_custom_check_host::run_custom_check_host;
use crate::hosting::main::run_repository_custom_rule_host::run_repository_custom_rule_host;
use crate::models::{CliOutput, Config, RepositoryRulePolicy};

const COMMAND_ERROR_EXIT_CODE: i32 = 2;

struct StructuredCheckRequest<'a> {
    arguments: &'a [String],
    python_targets: &'a [String],
    native_targets: &'a HashSet<String>,
    python_has_custom: bool,
    repository_selected: bool,
    repository_policy: Option<&'a RepositoryRulePolicy>,
}

pub(crate) fn partitioned_check(
    arguments: &[String],
    loaded: &[(PathBuf, Config)],
    repository_policy: Option<&RepositoryRulePolicy>,
) -> Option<CliOutput> {
    let show_warnings = arguments
        .iter()
        .any(|argument| argument == CHECK_WARN_ARGUMENT);
    let repository_selected =
        repository_policy.is_some_and(|policy| repository_rules_selected(policy, show_warnings));
    let mut python_has_custom = false;
    let mut python_targets: Vec<String> = Vec::new();
    let mut native_targets: HashSet<String> = HashSet::new();
    for (_, config) in loaded {
        if config.analyzer == AnalyzerId::Python {
            python_has_custom |= !config.rule_paths.is_empty()
                || !config.rule_modules.is_empty()
                || config.rule_options.keys().any(|code| code.starts_with('X'));
            if let Some(target) = &config.target {
                python_targets.push(target.clone());
                if repository_selected && !python_has_custom {
                    native_targets.insert(target.clone());
                }
            }
        } else {
            if let Some(target) = &config.target {
                native_targets.insert(target.clone());
            }
        }
    }
    if !python_has_custom && !repository_selected {
        return None;
    }
    if repository_selected && !python_has_custom {
        native_targets.extend(python_targets.iter().cloned());
    } else if repository_selected {
        for target in &python_targets {
            native_targets.remove(target);
        }
    }
    let effective_arguments = aggregate_cache_arguments(arguments, loaded);
    Some(structured_check(StructuredCheckRequest {
        arguments: &effective_arguments,
        python_targets: &python_targets,
        native_targets: &native_targets,
        python_has_custom,
        repository_selected,
        repository_policy,
    }))
}

fn repository_rules_selected(policy: &RepositoryRulePolicy, show_warnings: bool) -> bool {
    let configured = !policy.rule_paths.is_empty()
        || !policy.rule_modules.is_empty()
        || policy.has_custom_options;
    configured
        && (policy.has_custom_options
            || policy
                .select
                .iter()
                .any(|selector| custom_selector_not_ignored(selector, &policy.ignore))
            || show_warnings
                && policy
                    .warn
                    .iter()
                    .any(|selector| custom_selector_not_ignored(selector, &policy.ignore)))
}

fn custom_selector_not_ignored(selector: &str, ignores: &[String]) -> bool {
    selector.starts_with('X')
        && !ignores
            .iter()
            .any(|ignored| ignored.starts_with('X') && selector.starts_with(ignored))
}

fn aggregate_cache_arguments(arguments: &[String], loaded: &[(PathBuf, Config)]) -> Vec<String> {
    let mut effective = arguments.to_vec();
    let cache_overridden = arguments
        .iter()
        .any(|argument| matches!(argument.as_str(), "--cache" | "--no-cache"));
    if !cache_overridden && !loaded.iter().all(|(_, config)| config.cache_enabled) {
        effective.push("--no-cache".to_owned());
    }
    effective
}

fn structured_check(request: StructuredCheckRequest<'_>) -> CliOutput {
    let StructuredCheckRequest {
        arguments,
        python_targets,
        native_targets,
        python_has_custom,
        repository_selected,
        repository_policy,
    } = request;
    let options = match check_output_options(arguments) {
        Ok(options) => options,
        Err(error) => return CliOutput::error(error),
    };
    let mut results: Vec<CheckResult> = Vec::new();
    let mut cache: Option<CheckCacheStats> = None;
    let mut messages: Vec<String> = Vec::new();
    let mut command_error = false;
    let mut show_cache_stats = options.show_cache_stats;
    if python_has_custom {
        match run_custom_check_host(arguments, python_targets) {
            Ok(response) => {
                show_cache_stats |= response.show_cache_stats;
                results.extend(response.results);
                cache = merged_cache(cache, response.cache.as_ref());
                messages.extend(response.messages);
                if let Some(error) = response.error {
                    messages.push(error);
                    command_error = true;
                }
            }
            Err(error) => {
                messages.push(error);
                command_error = true;
            }
        }
    }
    let mut root = std::env::current_dir().unwrap_or_default();
    let mut color = options.color;
    let mut show_warnings = options.show_warnings;
    let mut repository_targets: Vec<RepositoryTargetPayload> = Vec::new();
    if !native_targets.is_empty() {
        match execute_structured_check(arguments, native_targets, repository_selected) {
            Ok(native) => {
                root = native.root;
                color = native.color;
                show_warnings = native.show_warnings;
                results.extend(native.results);
                cache = merged_cache(cache, native.cache.as_ref());
                messages.extend(native.messages);
                repository_targets.extend(native.repository_targets);
            }
            Err(error) => {
                messages.push(error);
                command_error = true;
            }
        }
    }
    if repository_selected && python_has_custom && !python_targets.is_empty() {
        let names = python_targets.iter().cloned().collect::<HashSet<_>>();
        match repository_python_targets(arguments, &names) {
            Ok(targets) => repository_targets.extend(targets),
            Err(error) => {
                messages.push(error);
                command_error = true;
            }
        }
    }
    if repository_selected && !command_error {
        repository_targets.sort_by(|left, right| left.name.cmp(&right.name));
        let target_names = repository_targets
            .iter()
            .map(|target| target.name.clone())
            .collect::<HashSet<_>>();
        let cache_enabled = repository_cache_enabled(arguments, repository_policy);
        match run_repository_custom_rule_host(RepositoryCustomRulePayload {
            show_warnings: options.show_warnings,
            cache_enabled,
            targets: repository_targets,
        }) {
            Ok(response) => {
                cache = merged_cache(cache, response.cache.as_ref());
                match repository_result(response, &root, &target_names) {
                    Ok(result) => results.push(result),
                    Err(error) => {
                        messages.push(error);
                        command_error = true;
                    }
                }
            }
            Err(error) => {
                messages.push(error);
                command_error = true;
            }
        }
    }
    let (stdout, report_exit_code) = if command_error && results.is_empty() {
        (String::new(), 0)
    } else {
        render_check_results(results, &root, color, show_warnings)
    };
    let mut stderr = String::new();
    if show_cache_stats {
        if let Some(stats) = cache {
            stderr.push_str(&format!(
                "Cache: hits={} misses={} invalidations={} writes={} non_cacheable={}\n",
                stats.hits, stats.misses, stats.invalidations, stats.writes, stats.non_cacheable
            ));
        }
    }
    for message in messages {
        stderr.push_str(&message);
        stderr.push('\n');
    }
    CliOutput {
        stdout,
        stderr,
        exit_code: if command_error {
            COMMAND_ERROR_EXIT_CODE
        } else {
            report_exit_code
        },
    }
}

fn repository_cache_enabled(arguments: &[String], policy: Option<&RepositoryRulePolicy>) -> bool {
    if arguments
        .iter()
        .any(|argument| argument == CHECK_NO_CACHE_ARGUMENT)
    {
        return false;
    }
    arguments
        .iter()
        .any(|argument| argument == CHECK_CACHE_ARGUMENT)
        || policy.is_some_and(|value| value.cache_enabled)
}

fn repository_result(
    response: RepositoryCustomRuleResponse,
    root: &Path,
    target_names: &HashSet<String>,
) -> Result<CheckResult, String> {
    let blocking = response.blocking_codes.iter().collect::<HashSet<_>>();
    let warnings = response.warning_codes.iter().collect::<HashSet<_>>();
    if blocking.len() != response.blocking_codes.len()
        || warnings.len() != response.warning_codes.len()
        || !blocking.is_disjoint(&warnings)
        || blocking
            .iter()
            .chain(&warnings)
            .any(|code| !code.starts_with('X'))
    {
        return Err(
            "Repository custom-rule host returned duplicate or overlapping rule tiers.".to_owned(),
        );
    }
    for dependency in &response.dependencies {
        if dependency.requester != REPOSITORY_RULE_REQUESTER
            || dependency.target.is_empty()
            || !target_names.contains(&dependency.target)
            || !REPOSITORY_CUSTOM_DEPENDENCY_KINDS.contains(&dependency.kind.as_str())
            || dependency.query.is_empty()
            || dependency.query.contains('\\')
        {
            return Err("Repository custom-rule host returned an invalid dependency.".to_owned());
        }
    }
    let mut faults: Vec<crate::models::Fault> = Vec::new();
    for finding in response.findings {
        if !confined_repository_path(&finding.path) {
            return Err(
                "Repository custom-rule host returned an unconfined finding path.".to_owned(),
            );
        }
        let valid_severity = match finding.severity {
            FindingSeverity::Blocking => blocking.contains(&finding.code),
            FindingSeverity::Warning => warnings.contains(&finding.code),
        };
        if !valid_severity {
            return Err("Repository custom-rule host returned inconsistent severity.".to_owned());
        }
        if !finding.code.starts_with('X') {
            return Err("Repository custom-rule host returned a non-custom rule code.".to_owned());
        }
        faults.push(crate::models::Fault {
            warning: finding.severity == FindingSeverity::Warning,
            code: finding.code,
            alias_of: None,
            path: root.join(finding.path).to_string_lossy().into_owned(),
            line: finding.line,
            column: finding.column,
            message: finding.message,
            remediation: finding.remediation,
        });
    }
    let (blocking_faults, warning_faults) = faults.into_iter().partition(|fault| !fault.warning);
    Ok(CheckResult {
        analyzer: AnalyzerId::Python,
        faults: blocking_faults,
        warnings: warning_faults,
        selected: 0,
        excluded: 0,
        applied_exceptions: response.applied_exceptions,
        threshold_uses: Vec::new(),
        cacheable: Some(response.cacheable),
    })
}

fn confined_repository_path(value: &str) -> bool {
    if value == PROJECT_ROOT_PATH {
        return true;
    }
    let path = Path::new(value);
    !value.is_empty()
        && !value.contains('\\')
        && !path.is_absolute()
        && path.components().all(|component| {
            matches!(component, std::path::Component::Normal(_))
                && !component.as_os_str().to_string_lossy().ends_with(':')
        })
}

fn merged_cache(
    combined: Option<CheckCacheStats>,
    value: Option<&CheckCacheStats>,
) -> Option<CheckCacheStats> {
    let Some(value) = value else {
        return combined;
    };
    if let Some(mut combined) = combined {
        combined.merge(value);
        Some(combined)
    } else {
        Some(value.clone())
    }
}
