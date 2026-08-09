use std::cmp::Reverse;
use std::collections::{HashMap, HashSet};

use crate::catalogue::main::rule_catalogue::configured_rule_catalogue;
use crate::catalogue::main::rule_metadata::rule_metadata;
use crate::catalogue::main::validate_config_selectors::validate_config_selectors;
use crate::catalogue::models::RuleMetadata;
use crate::check::_helpers::policy::{path_matches, role};
use crate::models::{Config, ScopedSource, ThresholdUse};

const PATH_SEPARATOR: char = '/';
const RECURSIVE_GLOB: &str = "**";
const WILDCARD: char = '*';

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
    let mut rules: Vec<&'static RuleMetadata> = Vec::new();
    for rule in configured_rule_catalogue(&config.rule_packs)? {
        if !rule.analyzers.contains(&config.analyzer) {
            continue;
        }
        let selected = matches_selector(&rule.code, select);
        let explicit = select.iter().any(|selector| selector == &rule.code);
        let ignored = matches_selector(&rule.code, ignore);
        if (rule.enabled_by_default && selected || explicit) && !ignored {
            rules.push(rule);
        }
    }
    validate_unique_implementations(&rules)?;
    Ok(rules)
}

pub(crate) fn validate_config_tiers(config: &Config) -> Result<(), String> {
    let configured_catalogue = configured_rule_catalogue(&config.rule_packs)?;
    let catalogue = configured_catalogue
        .iter()
        .copied()
        .filter(|rule| rule.analyzers.contains(&config.analyzer))
        .collect::<Vec<_>>();
    validate_config_selectors(config, &catalogue, &configured_catalogue)?;
    let blocking = selected_rules(config, &config.select, &[])?;
    let warnings = selected_rules(config, &config.warn, &[])?;
    let warning_codes = warnings
        .iter()
        .map(|rule| rule.code.as_str())
        .collect::<HashSet<_>>();
    if let Some(rule) = blocking
        .iter()
        .find(|rule| warning_codes.contains(rule.code.as_str()))
    {
        return Err(format!(
            "Rule {} cannot be configured as both blocking and warning.",
            rule.code
        ));
    }
    let ignored_codes = configured_rule_catalogue(&config.rule_packs)?
        .into_iter()
        .filter(|rule| rule.analyzers.contains(&config.analyzer))
        .filter(|rule| matches_selector(&rule.code, &config.ignore))
        .map(|rule| rule.code.as_str())
        .collect::<HashSet<_>>();
    if let Some(rule) = warnings
        .iter()
        .find(|rule| ignored_codes.contains(rule.code.as_str()))
    {
        return Err(format!(
            "Rule {} cannot be configured as both warning and ignored.",
            rule.code
        ));
    }
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
                if !path_matches(&source.target_path, pattern) {
                    continue;
                }
                let rank = (path_specificity(pattern), order, pattern_order);
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

fn matches_selector(code: &str, selectors: &[String]) -> bool {
    selectors.iter().any(|selector| code.starts_with(selector))
}

fn path_specificity(pattern: &str) -> (usize, usize, Reverse<usize>, Reverse<usize>) {
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

pub(crate) fn validate_unique_implementations(rules: &[&RuleMetadata]) -> Result<(), String> {
    let codes = rules
        .iter()
        .map(|rule| rule.code.clone())
        .collect::<Vec<_>>();
    let _ = display_codes_by_implementation(&codes)?;
    Ok(())
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
