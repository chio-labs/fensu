use std::collections::{HashMap, HashSet};
use std::path::Path;

use serde_json::json;

use crate::helpers::{process, rule};
use crate::models::{Config, RuleMetadata};
use crate::skills::helpers::context::option_validation::validate_rule_options;
use crate::skills::models::{HostResponse, RuleSelection};

const CORE_KIND: &str = "core";
const CORE_PREFIX: &str = "FF";
const CORE_RULE_CODE_LENGTH: usize = 6;
const CUSTOM_KIND: &str = "custom";
const CUSTOM_PREFIX: char = 'X';
const MAX_CORE_SELECTOR_SUFFIX: usize = 4;
const METADATA_PROTOCOL: u32 = 2;

pub(crate) fn validate_config_policy(config: &Config) -> Result<(), String> {
    for (name, selectors) in [
        ("select", &config.select),
        ("warn", &config.warn),
        ("ignore", &config.ignore),
    ] {
        for selector in selectors {
            if !valid_selector(selector) {
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
        || !config.rule_options.is_empty()
    {
        return hosted_selection(project_root);
    }
    let catalogue = rule::catalogue().to_vec();
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

fn hosted_selection(project_root: &Path) -> Result<RuleSelection, String> {
    let request = serde_json::to_vec(&json!({
        "protocol": METADATA_PROTOCOL,
        "project_root": project_root.to_string_lossy(),
    }))
    .map_err(|error| error.to_string())?;
    let raw = process::run_skills_metadata_host(&request)?;
    validate_host_shape(&raw)?;
    let response: HostResponse = serde_json::from_slice(&raw)
        .map_err(|error| format!("Invalid custom-rule metadata host response: {error}"))?;
    if response.protocol != METADATA_PROTOCOL {
        return Err(format!(
            "Incompatible custom-rule metadata protocol {}; expected {}.",
            response.protocol, METADATA_PROTOCOL
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
        "source",
        "cacheable",
        "options",
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
    let mut seen = HashSet::new();
    for item in catalogue {
        if !valid_code(&item.code) {
            return Err(format!(
                "Catalogue rule {} must use one exact rule code.",
                item.code
            ));
        }
        let core = item.code.starts_with(CORE_PREFIX);
        if (core && item.kind != CORE_KIND) || (!core && item.kind != CUSTOM_KIND) {
            return Err(format!(
                "Catalogue rule {} has incompatible kind {}.",
                item.code, item.kind
            ));
        }
        if !core && !item.code.starts_with(CUSTOM_PREFIX) {
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
            || (item.kind == CORE_KIND && item.source.is_some())
        {
            return Err(format!(
                "Catalogue rule {} contains incompatible metadata.",
                item.code
            ));
        }
        validate_rule_options(item)?;
    }
    Ok(())
}

fn tier_from_codes(
    codes: &[String],
    catalogue: &HashMap<&str, RuleMetadata>,
    tier: &str,
) -> Result<Vec<RuleMetadata>, String> {
    let mut seen = HashSet::new();
    let mut result = Vec::new();
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
    catalogue
        .iter()
        .filter(|item| {
            (item.enabled_by_default && selectors.iter().any(|value| item.code.starts_with(value)))
                || selectors
                    .iter()
                    .any(|value| valid_code(value) && value == &item.code)
        })
        .cloned()
        .collect()
}

fn matching(catalogue: &[RuleMetadata], selectors: &[String]) -> Vec<RuleMetadata> {
    catalogue
        .iter()
        .filter(|item| selectors.iter().any(|value| item.code.starts_with(value)))
        .cloned()
        .collect()
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

fn valid_code(value: &str) -> bool {
    let bytes = value.as_bytes();
    (bytes.len() == CORE_RULE_CODE_LENGTH
        && value.starts_with(CORE_PREFIX)
        && bytes[2].is_ascii_uppercase()
        && bytes[3..].iter().all(u8::is_ascii_digit))
        || value.strip_prefix(CUSTOM_PREFIX).is_some_and(|rest| {
            let digit = rest.find(|character: char| character.is_ascii_digit());
            digit.is_some_and(|index| {
                rest[..index]
                    .chars()
                    .all(|character| character.is_ascii_uppercase())
                    && !rest[index..].is_empty()
                    && rest[index..]
                        .chars()
                        .all(|character| character.is_ascii_digit())
            })
        })
}

fn valid_selector(value: &str) -> bool {
    if value == CORE_PREFIX || value == CUSTOM_PREFIX.to_string() {
        return true;
    }
    if let Some(rest) = value.strip_prefix(CORE_PREFIX) {
        return rest.len() <= MAX_CORE_SELECTOR_SUFFIX
            && rest
                .chars()
                .next()
                .is_some_and(|item| item.is_ascii_uppercase())
            && rest[1..].chars().all(|item| item.is_ascii_digit());
    }
    value.strip_prefix(CUSTOM_PREFIX).is_some_and(|rest| {
        let digit = rest
            .find(|character: char| character.is_ascii_digit())
            .unwrap_or(rest.len());
        rest[..digit].chars().all(|item| item.is_ascii_uppercase())
            && rest[digit..].chars().all(|item| item.is_ascii_digit())
    })
}
