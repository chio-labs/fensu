//! Partition mixed custom-Python and native-web aggregate checks.

use std::collections::HashSet;
use std::path::PathBuf;

use crate::analyzer::AnalyzerId;
use crate::command::main::check;
use crate::hosting::main::run_custom_check_host::run_custom_check_host;
use crate::models::{CliOutput, Config};

const CACHE_FIELD_COUNT: usize = 5;
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
            || !config.rule_options.is_empty();
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
    let hosted = run_custom_check_host(&effective_arguments, &python_targets)
        .unwrap_or_else(CliOutput::error);
    let native = if web_targets.is_empty() {
        None
    } else {
        Some(check::run(&effective_arguments, Some(&web_targets)).unwrap_or_else(CliOutput::error))
    };
    Some(merge_check_outputs(hosted, native))
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

fn merge_check_outputs(hosted: CliOutput, native: Option<CliOutput>) -> CliOutput {
    let Some(native) = native else {
        return hosted;
    };
    let exit_code = if hosted.exit_code >= COMMAND_ERROR_EXIT_CODE
        || native.exit_code >= COMMAND_ERROR_EXIT_CODE
    {
        COMMAND_ERROR_EXIT_CODE
    } else {
        hosted.exit_code.max(native.exit_code)
    };
    let (hosted_stderr, hosted_stats) = without_cache_stats(&hosted.stderr);
    let (native_stderr, native_stats) = without_cache_stats(&native.stderr);
    let mut stderr = String::new();
    if let Some(stats) = combined_cache_stats(hosted_stats, native_stats) {
        stderr.push_str(&format!(
            "Cache: hits={} misses={} invalidations={} writes={} non_cacheable={}\n",
            stats[0], stats[1], stats[2], stats[3], stats[4]
        ));
    }
    stderr.push_str(&hosted_stderr);
    stderr.push_str(&native_stderr);
    CliOutput {
        stdout: format!("{}{}", hosted.stdout, native.stdout),
        stderr,
        exit_code,
    }
}

fn without_cache_stats(stderr: &str) -> (String, Option<[usize; CACHE_FIELD_COUNT]>) {
    let mut retained = String::new();
    let mut stats = None;
    for line in stderr.split_inclusive('\n') {
        if let Some(parsed) = parse_cache_stats(line.trim_end()) {
            stats = Some(parsed);
        } else {
            retained.push_str(line);
        }
    }
    (retained, stats)
}

fn parse_cache_stats(line: &str) -> Option<[usize; CACHE_FIELD_COUNT]> {
    let values = line
        .strip_prefix("Cache: ")?
        .split_whitespace()
        .collect::<Vec<_>>();
    let keys = ["hits", "misses", "invalidations", "writes", "non_cacheable"];
    if values.len() < keys.len() {
        return None;
    }
    let mut parsed = [0; CACHE_FIELD_COUNT];
    for (index, (value, key)) in values.iter().zip(keys).enumerate() {
        let raw = value.strip_prefix(&format!("{key}="))?;
        let Ok(number) = raw.parse() else {
            return None;
        };
        parsed[index] = number;
    }
    Some(parsed)
}

fn combined_cache_stats(
    left: Option<[usize; CACHE_FIELD_COUNT]>,
    right: Option<[usize; CACHE_FIELD_COUNT]>,
) -> Option<[usize; CACHE_FIELD_COUNT]> {
    match (left, right) {
        (Some(left), Some(right)) => Some(std::array::from_fn(|index| left[index] + right[index])),
        (Some(stats), None) | (None, Some(stats)) => Some(stats),
        (None, None) => None,
    }
}
