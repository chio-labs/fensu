//! Partition mixed custom-Python and native-web aggregate checks.

use std::collections::HashSet;
use std::path::PathBuf;

use crate::analyzer::AnalyzerId;
use crate::check::main::check_output_options::check_output_options;
use crate::check::main::execute_structured_check::execute_structured_check;
use crate::check::main::render_check_results::render_check_results;
use crate::check::models::{CheckCacheStats, CheckResult};
use crate::hosting::main::run_custom_check_host::run_custom_check_host;
use crate::models::{CliOutput, Config};

const COMMAND_ERROR_EXIT_CODE: i32 = 2;

pub(crate) fn partitioned_check(
    arguments: &[String],
    loaded: &[(PathBuf, Config)],
) -> Option<CliOutput> {
    let mut hosted_web_policy = false;
    let mut python_has_custom = false;
    let mut python_targets: Vec<String> = Vec::new();
    let mut web_targets: HashSet<String> = HashSet::new();
    for (_, config) in loaded {
        let hosted_policy = !config.rule_paths.is_empty()
            || !config.rule_modules.is_empty()
            || config
                .rule_options
                .keys()
                .any(|code| config.analyzer != AnalyzerId::Rust || code.starts_with('X'));
        if config.analyzer == AnalyzerId::Python {
            python_has_custom |= !config.rule_paths.is_empty()
                || !config.rule_modules.is_empty()
                || config.rule_options.keys().any(|code| code.starts_with('X'));
            if let Some(target) = &config.target {
                python_targets.push(target.clone());
            }
        } else {
            hosted_web_policy |= hosted_policy;
            if let Some(target) = &config.target {
                web_targets.insert(target.clone());
            }
        }
    }
    if !python_has_custom || hosted_web_policy {
        return None;
    }
    let effective_arguments = aggregate_cache_arguments(arguments, loaded);
    Some(structured_check(
        &effective_arguments,
        &python_targets,
        &web_targets,
    ))
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

fn structured_check(
    arguments: &[String],
    python_targets: &[String],
    web_targets: &HashSet<String>,
) -> CliOutput {
    let options = match check_output_options(arguments) {
        Ok(options) => options,
        Err(error) => return CliOutput::error(error),
    };
    let mut results: Vec<CheckResult> = Vec::new();
    let mut cache: Option<CheckCacheStats> = None;
    let mut messages: Vec<String> = Vec::new();
    let mut command_error = false;
    let hosted = run_custom_check_host(arguments, python_targets);
    let show_cache_stats = hosted
        .as_ref()
        .is_ok_and(|response| response.show_cache_stats)
        || options.show_cache_stats;
    match hosted {
        Ok(response) => {
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
    let mut root = std::env::current_dir().unwrap_or_default();
    let mut color = options.color;
    let mut show_warnings = options.show_warnings;
    if !web_targets.is_empty() {
        match execute_structured_check(arguments, web_targets) {
            Ok(native) => {
                root = native.root;
                color = native.color;
                show_warnings = native.show_warnings;
                results.extend(native.results);
                cache = merged_cache(cache, native.cache.as_ref());
                messages.extend(native.messages);
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
