use std::collections::{HashMap, HashSet};
use std::path::Path;

use serde_json::json;

use crate::catalogue::main::rule_catalogue::configured_rule_catalogue;
use crate::catalogue::main::validate_config_selectors::validate_config_selectors;
use crate::catalogue::models::RuleMetadata;
use crate::configuration::constants::{
    CONTRACT_BEHAVIORS, DEFAULT_THRESHOLDS, RULE_CONFIGURATION_INPUTS,
    SKILLS_METADATA_PROTOCOL_VERSION,
};
use crate::configuration::main::is_rule_code::is_rule_code;
use crate::configuration::main::is_rule_selector::is_rule_selector;
use crate::hosting::main::run_skills_metadata_host::run_skills_metadata_host;
use crate::models::Config;
use crate::skills::_helpers::context::option_validation::validate_rule_options;
use crate::skills::models::{HostResponse, RuleSelection};

const CORE_KIND: &str = "core";
const CORE_PREFIX: &str = "FF";
const WEB_CORE_PREFIX: &str = "FW";
const CUSTOM_KIND: &str = "custom";
const CUSTOM_PREFIX: char = 'X';
const PACK_KIND: &str = "pack";
const PACK_PREFIX: &str = "FP";

pub(crate) fn validate_config_policy(config: &Config) -> Result<(), String> {
    for (name, selectors) in [
        ("select", &config.select),
        ("warn", &config.warn),
        ("ignore", &config.ignore),
    ] {
        for selector in selectors {
            if !is_rule_selector(selector) {
                return Err(format!(
                    "Config key {name} contains invalid selector {selector}."
                ));
            }
        }
    }
    Ok(())
}

pub(crate) fn selection(config: &Config, project_root: &Path) -> Result<RuleSelection, String> {
    if !config.rule_paths.is_empty()
        || !config.rule_modules.is_empty()
        || config.rule_options.keys().any(|code| code.starts_with('X'))
    {
        config.analyzer.require_backend()?;
        return hosted_selection(project_root, config.target.as_deref());
    }
    let configured_catalogue = configured_rule_catalogue(&config.rule_packs)?;
    let applicable_catalogue = configured_catalogue
        .iter()
        .copied()
        .filter(|rule| rule.analyzers.contains(&config.analyzer))
        .collect::<Vec<_>>();
    validate_config_selectors(config, &applicable_catalogue, &configured_catalogue)?;
    let catalogue = applicable_catalogue
        .into_iter()
        .cloned()
        .collect::<Vec<_>>();
    let ignored = matching(&catalogue, &config.ignore);
    let ignored_codes = ignored
        .iter()
        .map(|item| item.code.as_str())
        .collect::<HashSet<_>>();
    let blocking = selected(&catalogue, &config.select)
        .into_iter()
        .filter(|item| !ignored_codes.contains(item.code.as_str()))
        .collect::<Vec<_>>();
    let warnings = selected(&catalogue, &config.warn);
    validate_tiers(&blocking, &warnings, &ignored)?;
    Ok(RuleSelection {
        catalogue,
        blocking,
        warnings,
        ignored,
    })
}

fn hosted_selection(project_root: &Path, target: Option<&str>) -> Result<RuleSelection, String> {
    let request = serde_json::to_vec(&json!({
        "protocol": SKILLS_METADATA_PROTOCOL_VERSION,
        "project_root": project_root.to_string_lossy(),
        "target": target,
    }))
    .map_err(|error| error.to_string())?;
    let raw = run_skills_metadata_host(&request)?;
    validate_host_shape(&raw)?;
    let response: HostResponse = serde_json::from_slice(&raw)
        .map_err(|error| format!("Invalid custom-rule metadata host response: {error}"))?;
    if response.protocol != SKILLS_METADATA_PROTOCOL_VERSION {
        return Err(format!(
            "Incompatible custom-rule metadata protocol {}; expected {}.",
            response.protocol, SKILLS_METADATA_PROTOCOL_VERSION
        ));
    }
    if response.package_version != env!("CARGO_PKG_VERSION") {
        return Err(format!(
            "Custom-rule metadata host version {} does not match native fensu {}.",
            response.package_version,
            env!("CARGO_PKG_VERSION")
        ));
    }
    validate_host_catalogue(&response.catalogue)?;
    let by_code = response
        .catalogue
        .iter()
        .map(|item| (item.code.as_str(), item.clone()))
        .collect::<HashMap<_, _>>();
    let blocking = tier_from_codes(&response.blocking, &by_code, "blocking")?;
    let warnings = tier_from_codes(&response.warnings, &by_code, "warnings")?;
    let ignored = tier_from_codes(&response.ignored, &by_code, "ignored")?;
    validate_tiers(&blocking, &warnings, &ignored)?;
    Ok(RuleSelection {
        catalogue: response.catalogue,
        blocking,
        warnings,
        ignored,
    })
}

fn validate_host_shape(raw: &[u8]) -> Result<(), String> {
    let value: serde_json::Value = serde_json::from_slice(raw)
        .map_err(|error| format!("Invalid custom-rule metadata host response: {error}"))?;
    let catalogue = value
        .get("catalogue")
        .and_then(serde_json::Value::as_array)
        .ok_or_else(|| "Custom-rule metadata host response has no catalogue array.".to_owned())?;
    let expected = HashSet::from([
        "code",
        "family",
        "slug",
        "message",
        "remediation",
        "severity",
        "enabled_by_default",
        "execution_owner",
        "kind",
        "pack",
        "alias_of",
        "analyzers",
        "source",
        "cacheable",
        "options",
        "constraints",
        "thresholds",
        "contract_behaviors",
        "configuration_inputs",
        "limits",
    ]);
    for rule in catalogue {
        let fields = rule
            .as_object()
            .ok_or_else(|| "Custom-rule catalogue entry must be an object.".to_owned())?
            .keys()
            .map(String::as_str)
            .collect::<HashSet<_>>();
        if fields != expected {
            return Err("Custom-rule catalogue entry has an incompatible schema.".to_owned());
        }
    }
    Ok(())
}

fn validate_host_catalogue(catalogue: &[RuleMetadata]) -> Result<(), String> {
    let mut seen: HashSet<String> = HashSet::new();
    for item in catalogue {
        if !is_rule_code(&item.code) {
            return Err(format!(
                "Catalogue rule {} must use one exact rule code.",
                item.code
            ));
        }
        let core = item.code.starts_with(CORE_PREFIX) || item.code.starts_with(WEB_CORE_PREFIX);
        let pack = item.code.starts_with(PACK_PREFIX);
        if (core && item.kind != CORE_KIND)
            || (pack && item.kind != PACK_KIND)
            || (!core && !pack && item.kind != CUSTOM_KIND)
        {
            return Err(format!(
                "Catalogue rule {} has incompatible kind {}.",
                item.code, item.kind
            ));
        }
        if !core && !pack && !item.code.starts_with(CUSTOM_PREFIX) {
            return Err(format!(
                "Custom rule {} must use the X* namespace.",
                item.code
            ));
        }
        if !seen.insert(item.code.clone()) {
            return Err(format!(
                "Duplicate rule code {} in custom metadata.",
                item.code
            ));
        }
        if item.family.is_empty()
            || item.slug.is_empty()
            || item.message.is_empty()
            || !matches!(item.severity.as_str(), "error" | "warning")
            || !matches!(
                item.execution_owner.as_str(),
                "file" | "package" | "domain" | "subdomain" | "leaf" | "scope" | "project"
            )
            || (item.kind == CUSTOM_KIND && item.source.as_deref().is_none_or(str::is_empty))
            || (item.kind == CORE_KIND && (item.source.is_some() || item.pack.is_some()))
            || (item.kind == PACK_KIND
                && (item.pack.as_deref().is_none_or(str::is_empty) || item.source.is_some()))
            || item
                .alias_of
                .as_ref()
                .is_some_and(|target| target == &item.code)
            || item.analyzers.is_empty()
            || item.analyzers.iter().collect::<HashSet<_>>().len() != item.analyzers.len()
            || (item.kind == CUSTOM_KIND
                && item.analyzers.as_slice() != [crate::analyzer::AnalyzerId::Python])
        {
            return Err(format!(
                "Catalogue rule {} contains incompatible metadata.",
                item.code
            ));
        }
        validate_rule_options(item)?;
        validate_rule_constraints(item)?;
        validate_rule_inputs(item)?;
        validate_rule_limits(item)?;
    }
    Ok(())
}

fn validate_rule_limits(rule: &RuleMetadata) -> Result<(), String> {
    let mut names: HashSet<&str> = HashSet::new();
    if rule.limits.iter().any(|limit| {
        limit.name.is_empty() || limit.description.is_empty() || !names.insert(&limit.name)
    }) {
        return Err(format!(
            "Catalogue rule {} contains an incompatible fixed limit.",
            rule.code
        ));
    }
    Ok(())
}

fn validate_rule_inputs(rule: &RuleMetadata) -> Result<(), String> {
    let threshold_names = DEFAULT_THRESHOLDS
        .iter()
        .map(|(name, _)| *name)
        .collect::<HashSet<_>>();
    let unique_thresholds = rule.thresholds.iter().collect::<HashSet<_>>();
    let unique_behaviors = rule.contract_behaviors.iter().collect::<HashSet<_>>();
    let unique_configuration = rule.configuration_inputs.iter().collect::<HashSet<_>>();
    if unique_thresholds.len() != rule.thresholds.len()
        || rule
            .thresholds
            .iter()
            .any(|name| !threshold_names.contains(name.as_str()))
        || unique_behaviors.len() != rule.contract_behaviors.len()
        || rule
            .contract_behaviors
            .iter()
            .any(|behavior| !CONTRACT_BEHAVIORS.contains(&behavior.as_str()))
        || unique_configuration.len() != rule.configuration_inputs.len()
        || rule
            .configuration_inputs
            .iter()
            .any(|name| !RULE_CONFIGURATION_INPUTS.contains(&name.as_str()))
    {
        return Err(format!(
            "Catalogue rule {} contains incompatible effective inputs.",
            rule.code
        ));
    }
    Ok(())
}

fn validate_rule_constraints(rule: &RuleMetadata) -> Result<(), String> {
    let mut names: HashSet<&str> = HashSet::new();
    for constraint in &rule.constraints {
        let unique_values = constraint.values.iter().collect::<HashSet<_>>();
        if constraint.name.is_empty()
            || constraint.description.is_empty()
            || constraint.values.is_empty()
            || unique_values.len() != constraint.values.len()
            || !names.insert(&constraint.name)
        {
            return Err(format!(
                "Catalogue rule {} contains an incompatible constraint.",
                rule.code
            ));
        }
    }
    Ok(())
}

fn tier_from_codes(
    codes: &[String],
    catalogue: &HashMap<&str, RuleMetadata>,
    tier: &str,
) -> Result<Vec<RuleMetadata>, String> {
    let mut seen: HashSet<&String> = HashSet::new();
    let mut result: Vec<RuleMetadata> = Vec::new();
    for code in codes {
        if !seen.insert(code) {
            return Err(format!("Duplicate {tier} tier member: {code}."));
        }
        result.push(
            catalogue
                .get(code.as_str())
                .cloned()
                .ok_or_else(|| format!("Unknown {tier} tier member: {code}."))?,
        );
    }
    Ok(result)
}

fn selected(catalogue: &[RuleMetadata], selectors: &[String]) -> Vec<RuleMetadata> {
    let mut selected: Vec<RuleMetadata> = Vec::new();
    for item in catalogue {
        let enabled =
            item.enabled_by_default && selectors.iter().any(|value| item.code.starts_with(value));
        let explicit = selectors
            .iter()
            .any(|value| is_rule_code(value) && value == &item.code);
        if enabled || explicit {
            selected.push(item.clone());
        }
    }
    selected
}

fn matching(catalogue: &[RuleMetadata], selectors: &[String]) -> Vec<RuleMetadata> {
    let mut matching: Vec<RuleMetadata> = Vec::new();
    for item in catalogue {
        if selectors.iter().any(|value| item.code.starts_with(value)) {
            matching.push(item.clone());
        }
    }
    matching
}

fn validate_tiers(
    blocking: &[RuleMetadata],
    warnings: &[RuleMetadata],
    ignored: &[RuleMetadata],
) -> Result<(), String> {
    let blocking = blocking
        .iter()
        .map(|item| &item.code)
        .collect::<HashSet<_>>();
    let warnings = warnings
        .iter()
        .map(|item| &item.code)
        .collect::<HashSet<_>>();
    let ignored = ignored
        .iter()
        .map(|item| &item.code)
        .collect::<HashSet<_>>();
    if let Some(code) = blocking.intersection(&warnings).next() {
        return Err(format!(
            "Rule {code} cannot be configured as both blocking and warning."
        ));
    }
    if let Some(code) = warnings.intersection(&ignored).next() {
        return Err(format!(
            "Rule {code} cannot be configured as both warning and ignored."
        ));
    }
    Ok(())
}
