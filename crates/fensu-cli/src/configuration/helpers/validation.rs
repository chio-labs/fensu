use std::collections::HashSet;

use crate::configuration::helpers::exceptions;
use crate::constants::{
    CONFIG_ROLE_NAMES, CONTRACT_BEHAVIORS, DEFAULT_THRESHOLDS, MAX_CORE_SELECTOR_SUFFIX,
};

const RECURSIVE_GLOB: &str = "**";

pub(crate) fn validate(table: &toml::map::Map<String, toml::Value>) -> Result<(), String> {
    validate_keys(
        table,
        &[
            "roots",
            "tests",
            "tooling",
            "select",
            "warn",
            "ignore",
            "rule_paths",
            "rule_modules",
            "thresholds",
            "roles",
            "contracts",
            "rule_exceptions",
            "rule_ignores",
            "threshold_overrides",
            "cache",
            "experimental",
            "memory",
            "evaluation",
            "skills",
        ],
        "",
    )
    .map_err(|error| error.replace("Unknown  config", "Unknown config"))?;
    validate_optional_table(table, "cache", &["enabled", "require_cacheable"])?;
    validate_optional_table(table, "evaluation", &["include", "exclude"])?;
    validate_optional_table(table, "skills", &["name"])?;
    for name in [
        "tests",
        "tooling",
        "select",
        "warn",
        "ignore",
        "rule_paths",
        "rule_modules",
    ] {
        if let Some(value) = table.get(name) {
            let _ = required_strings(Some(value), name)?;
        }
    }
    validate_nested_roots(required_strings(table.get("roots"), "roots")?)?;
    validate_boolean_table(table, "cache", &["enabled", "require_cacheable"])?;
    validate_boolean_table(table, "experimental", &["memory"])?;
    validate_threshold_table(table.get("thresholds"), "thresholds", false)?;
    validate_roles(table.get("roles"))?;
    validate_contracts(table.get("contracts"))?;
    validate_threshold_overrides(table.get("threshold_overrides"))?;
    exceptions::validate(table.get("rule_exceptions"))?;
    validate_rule_ignores(table.get("rule_ignores"))?;
    validate_evaluation(table.get("evaluation"))?;
    Ok(())
}

fn validate_nested_roots(roots: Vec<String>) -> Result<(), String> {
    for (index, first) in roots.iter().enumerate() {
        let first = first.split('/').collect::<Vec<_>>();
        for second in roots.iter().skip(index + 1) {
            let second = second.split('/').collect::<Vec<_>>();
            let length = first.len().min(second.len());
            if first[..length] == second[..length] {
                return Err("Config key roots must not contain nested paths.".to_owned());
            }
        }
    }
    Ok(())
}

fn validate_boolean_table(
    table: &toml::map::Map<String, toml::Value>,
    name: &str,
    keys: &[&str],
) -> Result<(), String> {
    let Some(values) = table.get(name).and_then(toml::Value::as_table) else {
        return Ok(());
    };
    for key in keys {
        if values.get(*key).is_some_and(|value| !value.is_bool()) {
            return Err(format!("Config key {name}.{key} must be a boolean."));
        }
    }
    Ok(())
}

fn validate_threshold_table(
    value: Option<&toml::Value>,
    owner: &str,
    required: bool,
) -> Result<(), String> {
    let Some(value) = value else {
        return if required {
            Err(format!(
                "Config key {owner} must be a table of integer thresholds."
            ))
        } else {
            Ok(())
        };
    };
    let values = value
        .as_table()
        .ok_or_else(|| format!("Config key {owner} must be a table of integer thresholds."))?;
    if required && values.is_empty() {
        return Err("Threshold override thresholds must be a non-empty inline table.".to_owned());
    }
    let known = DEFAULT_THRESHOLDS
        .iter()
        .map(|(name, _)| *name)
        .collect::<HashSet<_>>();
    for (name, value) in values {
        if !known.contains(name.as_str()) {
            return Err(format!("Unknown threshold key in {owner}: {name}."));
        }
        let Some(number) = value.as_integer() else {
            return Err(format!("Threshold {name} in {owner} must be an integer."));
        };
        if number < 0 {
            return Err(format!("Threshold {name} in {owner} must be non-negative."));
        }
        if u32::try_from(number).is_err() {
            return Err(format!("Threshold {name} in {owner} is too large."));
        }
    }
    Ok(())
}

fn validate_roles(value: Option<&toml::Value>) -> Result<(), String> {
    let Some(value) = value else {
        return Ok(());
    };
    let roles = value
        .as_table()
        .ok_or_else(|| "Config key roles must be a table of role threshold tables.".to_owned())?;
    for (role, thresholds) in roles {
        if !CONFIG_ROLE_NAMES.contains(&role.as_str()) {
            return Err(format!("Unknown role name in roles: {role}."));
        }
        validate_threshold_table(Some(thresholds), &format!("roles.{role}"), false)?;
    }
    Ok(())
}

fn validate_contracts(value: Option<&toml::Value>) -> Result<(), String> {
    let Some(value) = value else {
        return Ok(());
    };
    let contracts = value
        .as_table()
        .ok_or_else(|| "Config key contracts must be a table.".to_owned())?;
    for (pattern, behavior) in contracts {
        if pattern.is_empty() {
            return Err("Config contract patterns must be non-empty strings.".to_owned());
        }
        let behavior = behavior.as_str().unwrap_or_default();
        if !CONTRACT_BEHAVIORS.contains(&behavior) {
            return Err(format!(
                "Unknown contract behavior for {pattern}: {behavior}."
            ));
        }
    }
    Ok(())
}

fn validate_threshold_overrides(value: Option<&toml::Value>) -> Result<(), String> {
    let Some(value) = value else {
        return Ok(());
    };
    let entries = value
        .as_array()
        .ok_or_else(|| "Config key threshold_overrides must be an array of tables.".to_owned())?;
    for entry in entries {
        let table = entry.as_table().ok_or_else(|| {
            "Each threshold_overrides entry must define only paths, thresholds, and reason."
                .to_owned()
        })?;
        let expected = HashSet::from(["paths", "thresholds", "reason"]);
        let actual = table.keys().map(String::as_str).collect::<HashSet<_>>();
        if actual != expected {
            return Err(
                "Each threshold_overrides entry must define only paths, thresholds, and reason."
                    .to_owned(),
            );
        }
        let paths = required_strings(table.get("paths"), "threshold_overrides.paths")?;
        if paths.is_empty() {
            return Err("Threshold override paths must not be empty.".to_owned());
        }
        for path in paths {
            validate_path_pattern(&path, "Threshold override path")?;
        }
        if table
            .get("reason")
            .and_then(toml::Value::as_str)
            .is_none_or(|reason| reason.trim().is_empty())
        {
            return Err("Threshold override reason must be non-empty.".to_owned());
        }
        validate_threshold_table(
            table.get("thresholds"),
            "threshold_overrides.thresholds",
            true,
        )?;
    }
    Ok(())
}

fn validate_rule_ignores(value: Option<&toml::Value>) -> Result<(), String> {
    let Some(value) = value else {
        return Ok(());
    };
    let entries = value
        .as_array()
        .ok_or_else(|| "Config key rule_ignores must be an array of tables.".to_owned())?;
    for entry in entries {
        let table = entry.as_table().ok_or_else(|| {
            "Each rule_ignores entry must define only rules, paths, and reason.".to_owned()
        })?;
        let expected = HashSet::from(["rules", "paths", "reason"]);
        let actual = table.keys().map(String::as_str).collect::<HashSet<_>>();
        if actual != expected {
            return Err(
                "Each rule_ignores entry must define only rules, paths, and reason.".to_owned(),
            );
        }
        let rules = required_strings(table.get("rules"), "rule_ignores.rules")?;
        if rules.is_empty() {
            return Err("Rule ignore selectors must not be empty.".to_owned());
        }
        for selector in rules {
            if !valid_rule_selector(&selector) {
                return Err(format!(
                    "Config key rule_ignores.rules contains invalid selector {selector}."
                ));
            }
        }
        let paths = required_strings(table.get("paths"), "rule_ignores.paths")?;
        if paths.is_empty() {
            return Err("Rule ignore paths must not be empty.".to_owned());
        }
        for path in paths {
            validate_path_pattern(&path, "Rule ignore path")?;
        }
        if table
            .get("reason")
            .and_then(toml::Value::as_str)
            .is_none_or(|reason| reason.trim().is_empty())
        {
            return Err("Rule ignore reason must be non-empty.".to_owned());
        }
    }
    Ok(())
}

fn valid_rule_selector(value: &str) -> bool {
    if matches!(value, "FF" | "X") {
        return true;
    }
    if let Some(rest) = value.strip_prefix("FF") {
        return rest.len() <= MAX_CORE_SELECTOR_SUFFIX
            && rest
                .chars()
                .next()
                .is_some_and(|item| item.is_ascii_uppercase())
            && rest[1..].chars().all(|item| item.is_ascii_digit());
    }
    value.strip_prefix('X').is_some_and(|rest| {
        let digit = rest
            .find(|character: char| character.is_ascii_digit())
            .unwrap_or(rest.len());
        !rest.is_empty()
            && rest[..digit].chars().all(|item| item.is_ascii_uppercase())
            && rest[digit..].chars().all(|item| item.is_ascii_digit())
    })
}

fn validate_evaluation(value: Option<&toml::Value>) -> Result<(), String> {
    let Some(value) = value else {
        return Ok(());
    };
    let table = value
        .as_table()
        .ok_or_else(|| "Config key evaluation must be a table.".to_owned())?;
    for name in ["include", "exclude"] {
        let Some(value) = table.get(name) else {
            continue;
        };
        let patterns = required_strings(Some(value), &format!("evaluation.{name}"))?;
        if patterns.is_empty() {
            return Err(format!("Config key evaluation.{name} must not be empty."));
        }
        for pattern in patterns {
            validate_path_pattern(&pattern, &format!("Evaluation {name}"))?;
        }
    }
    Ok(())
}

fn validate_path_pattern(pattern: &str, owner: &str) -> Result<(), String> {
    let malformed = pattern.starts_with('/')
        || pattern.ends_with('/')
        || pattern.contains("//")
        || pattern.contains('\\')
        || pattern.contains(['?', '[', ']'])
        || pattern.split('/').any(|part| {
            matches!(part, "" | "." | "..")
                || part.contains(RECURSIVE_GLOB) && part != RECURSIVE_GLOB
        })
        || pattern.contains("**/**");
    if malformed {
        return Err(format!(
            "{owner} must be a repository-relative POSIX glob: {pattern}."
        ));
    }
    Ok(())
}

fn validate_optional_table(
    table: &toml::map::Map<String, toml::Value>,
    name: &str,
    keys: &[&str],
) -> Result<(), String> {
    let Some(value) = table.get(name) else {
        return Ok(());
    };
    let values = value
        .as_table()
        .ok_or_else(|| format!("Config key {name} must be a table."))?;
    validate_keys(values, keys, name)
}

pub(crate) fn validate_keys(
    table: &toml::map::Map<String, toml::Value>,
    allowed: &[&str],
    name: &str,
) -> Result<(), String> {
    let mut unknown = table
        .keys()
        .filter(|key| !allowed.contains(&key.as_str()))
        .cloned()
        .collect::<Vec<_>>();
    if unknown.is_empty() {
        return Ok(());
    }
    unknown.sort();
    Err(format!(
        "Unknown {name} config key(s): {}.",
        unknown.join(", ")
    ))
}

pub(crate) fn required_strings(
    value: Option<&toml::Value>,
    name: &str,
) -> Result<Vec<String>, String> {
    let value = value.ok_or_else(|| format!("Config key {name} must be a list of strings."))?;
    let items = value
        .as_array()
        .ok_or_else(|| format!("Config key {name} must be a list of strings."))?;
    let mut result = Vec::new();
    for item in items {
        let text = item
            .as_str()
            .filter(|text| !text.is_empty())
            .ok_or_else(|| format!("Config key {name} must contain non-empty strings."))?;
        result.push(text.to_owned());
    }
    Ok(result)
}
