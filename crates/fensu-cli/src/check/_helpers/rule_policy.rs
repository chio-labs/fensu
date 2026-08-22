use std::cmp::Reverse;
use std::collections::{HashMap, HashSet};

use fensu_policy::policy::errors::PolicyError;
use fensu_policy::policy::main::resolve_policy;
use fensu_policy::policy::main::validate_unique_implementations as generic_implementations;
use fensu_policy::policy::models::{FensuRuleCodeGrammar, PolicySelectors};
use fensu_policy::policy::types::PolicyTier;

use crate::catalogue::main::rule_catalogue::configured_rule_catalogue;
use crate::catalogue::main::rule_metadata::rule_metadata;
use crate::catalogue::main::validate_config_selectors::validate_config_selectors;
use crate::catalogue::models::RuleMetadata;
use crate::check::_helpers::policy::{path_matches, role};
use crate::configuration::main::expand_path_pattern::expand_path_pattern;
use crate::models::{Config, ScopedSource, ThresholdUse};

const PATH_SEPARATOR: char = '/';
const RECURSIVE_GLOB: &str = "**";
const WILDCARD: char = '*';
type PathSpecificity = (usize, usize, Reverse<usize>, Reverse<usize>);

pub(crate) fn display_codes_by_implementation(
    codes: &[String],
) -> Result<HashMap<String, String>, String> {
    let mut display: HashMap<String, String> = HashMap::new();
    for code in codes {
        let metadata =
            rule_metadata(code)?.ok_or_else(|| format!("Unknown native rule code: {code}"))?;
        let implementation = metadata.alias_of.as_ref().unwrap_or(code);
        if let Some(previous) = display.insert(implementation.clone(), code.clone()) {
            return Err(format!(
                "Rules {previous} and {code} select the same native implementation {implementation}; select only one identity."
            ));
        }
    }
    Ok(display)
}

pub(crate) fn selected_rules(
    config: &Config,
    select: &[String],
    ignore: &[String],
) -> Result<Vec<&'static RuleMetadata>, String> {
    let catalogue = configured_rule_catalogue(&config.rule_packs)?;
    let selection = resolve_policy::resolve_policy(
        &catalogue,
        &config.analyzer,
        &PolicySelectors {
            select: select.to_vec(),
            warn: Vec::new(),
            ignore: ignore.to_vec(),
        },
        &FensuRuleCodeGrammar,
    )
    .map_err(format_policy_error)?;
    let rules = selection.blocking;
    validate_unique_implementations(&rules)?;
    Ok(rules)
}

pub(crate) fn validate_config_tiers(config: &Config) -> Result<(), String> {
    let configured_catalogue = configured_rule_catalogue(&config.rule_packs)?;
    let catalogue = configured_catalogue
        .iter()
        .copied()
        .filter(|rule| applicable(rule, config))
        .collect::<Vec<_>>();
    validate_config_selectors(config, &catalogue, &configured_catalogue)?;
    let _ = resolve_policy::resolve_policy(
        &configured_catalogue,
        &config.analyzer,
        &PolicySelectors {
            select: config.select.clone(),
            warn: config.warn.clone(),
            ignore: config.ignore.clone(),
        },
        &FensuRuleCodeGrammar,
    )
    .map_err(format_policy_error)?;
    Ok(())
}

pub(crate) fn required_thresholds(codes: &[String]) -> Result<HashSet<&'static str>, String> {
    let mut names: HashSet<&'static str> = HashSet::new();
    for code in codes {
        if let Some(metadata) = rule_metadata(code)? {
            names.extend(metadata.thresholds.iter().map(String::as_str));
        }
    }
    Ok(names)
}

pub(crate) fn resolved_thresholds(
    source: &ScopedSource,
    config: &Config,
    codes: &[String],
) -> Result<(HashMap<String, u32>, Vec<ThresholdUse>), String> {
    let mut values = config.thresholds.clone();
    if let Some(role) = role(source).and_then(|role| config.role_thresholds.get(&role)) {
        values.extend(role.clone());
    }
    let mut uses: Vec<ThresholdUse> = Vec::new();
    for name in required_thresholds(codes)? {
        let mut winner = None;
        for (order, override_) in config.threshold_overrides.iter().enumerate() {
            let Some(value) = override_.thresholds.get(name) else {
                continue;
            };
            for (pattern_order, pattern) in override_.paths.iter().enumerate() {
                let Some(specificity) = matching_path_specificity(&source.target_path, pattern)?
                else {
                    continue;
                };
                let rank = (specificity, order, pattern_order);
                if winner
                    .as_ref()
                    .is_none_or(|(current, _, _, _, _)| rank >= *current)
                {
                    winner = Some((rank, order, pattern, &override_.reason, *value));
                }
            }
        }
        let Some((_, order, pattern, reason, value)) = winner else {
            continue;
        };
        values.insert(name.to_owned(), value);
        uses.push(ThresholdUse {
            repository_path: source.repository_path.clone(),
            threshold: name.to_owned(),
            override_order: order,
            matched_pattern: pattern.clone(),
            reason: reason.clone(),
            effective_value: value,
        });
    }
    Ok((values, uses))
}

pub(crate) fn applicable(rule: &RuleMetadata, config: &Config) -> bool {
    rule.analyzers.contains(&config.analyzer)
}

fn path_specificity(pattern: &str) -> PathSpecificity {
    let segments = pattern.split(PATH_SEPARATOR).collect::<Vec<_>>();
    let literal_segments = segments
        .iter()
        .filter(|segment| !segment.contains(WILDCARD))
        .count();
    let literal_characters = pattern
        .chars()
        .filter(|character| !matches!(character, &WILDCARD | &PATH_SEPARATOR))
        .count();
    let globstars = segments
        .iter()
        .filter(|segment| **segment == RECURSIVE_GLOB)
        .count();
    (
        literal_segments,
        literal_characters,
        Reverse(globstars),
        Reverse(wildcard_count(&segments)),
    )
}

fn matching_path_specificity(path: &str, pattern: &str) -> Result<Option<PathSpecificity>, String> {
    Ok(expand_path_pattern(pattern)?
        .into_iter()
        .filter_map(|expanded| path_matches(path, &expanded).then(|| path_specificity(&expanded)))
        .max())
}

pub(crate) fn validate_unique_implementations(rules: &[&RuleMetadata]) -> Result<(), String> {
    generic_implementations::validate_unique_implementations(rules).map_err(format_policy_error)
}

fn format_policy_error(error: PolicyError) -> String {
    match error {
        PolicyError::TierConflict {
            code,
            first: PolicyTier::Blocking,
            second: PolicyTier::Warning,
        } => format!("Rule {code} cannot be configured as both blocking and warning."),
        PolicyError::TierConflict {
            code,
            first: PolicyTier::Warning,
            second: PolicyTier::Ignored,
        } => format!("Rule {code} cannot be configured as both warning and ignored."),
        PolicyError::DuplicateImplementation {
            first_code,
            second_code,
            implementation_code,
        } => format!(
            "Rules {first_code} and {second_code} select the same native implementation {implementation_code}; select only one identity."
        ),
        other => format!("Invalid rule policy: {other}"),
    }
}

fn wildcard_count(segments: &[&str]) -> usize {
    let mut count = 0;
    for segment in segments {
        if *segment == RECURSIVE_GLOB {
            continue;
        }
        count += segment
            .chars()
            .filter(|character| *character == WILDCARD)
            .count();
    }
    count
}
