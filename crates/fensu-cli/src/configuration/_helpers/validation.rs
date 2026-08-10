use std::collections::{HashMap, HashSet};
use std::str::FromStr;

use crate::analyzer::AnalyzerId;
use crate::configuration::_helpers::exceptions;
use crate::configuration::_helpers::native_rules::{validate_rule_options, validate_rule_packs};
use crate::configuration::_helpers::roots::{normalize_target_root, validate_nested_roots};
use crate::configuration::_helpers::scopes::validate_test_scopes;
use crate::configuration::_helpers::selectors::valid_selector;
use crate::configuration::constants::{CONFIG_ROLE_NAMES, CONTRACT_BEHAVIORS, DEFAULT_THRESHOLDS};
use crate::configuration::main::expand_path_pattern::expand_path_pattern;
use crate::constants::CONFIG_TARGETS_KEY;
use crate::models::TargetSelection;

const RECURSIVE_GLOB: &str = "**";
const EVALUATION_INCLUDE: &str = "include";
const DEFAULT_TARGET_ROOT: &str = ".";
pub(crate) const WEB_THRESHOLD_ALIASES: &[(&str, &str)] = &[
    ("max_entry_statements", "max_statements"),
    ("max_entry_distinct_calls", "max_distinct_calls"),
    ("max_entry_locals", "max_locals"),
    ("max_function_statements", "max_statements_global"),
];
const CONFIG_KEYS: &[&str] = &[
    "roots",
    "tests",
    "test_scopes",
    "test_layout",
    "tooling",
    "generated",
    "select",
    "warn",
    "ignore",
    "rule_paths",
    "rule_modules",
    "rule_packs",
    "rule_options",
    "thresholds",
    "roles",
    "contracts",
    "ui_kit",
    "framework",
    "shadcn",
    "openapi",
    "rule_exceptions",
    "rule_ignores",
    "threshold_overrides",
    "cache",
    "evaluation",
    "skills",
];
type ValidatedTargets = HashMap<String, (toml::map::Map<String, toml::Value>, AnalyzerId, String)>;

pub(crate) fn validate(table: &toml::map::Map<String, toml::Value>) -> Result<(), String> {
    validate_for_analyzer(table, AnalyzerId::Python)
}

pub(crate) fn validate_for_analyzer(
    table: &toml::map::Map<String, toml::Value>,
    analyzer: AnalyzerId,
) -> Result<(), String> {
    validate_keys(table, CONFIG_KEYS, "")
        .map_err(|error| error.replace("Unknown  config", "Unknown config"))?;
    validate_optional_table(table, "cache", &["enabled", "require_cacheable"])?;
    validate_optional_table(table, "evaluation", &["include", "exclude"])?;
    validate_optional_table(table, "skills", &["name"])?;
    validate_rule_options(table.get("rule_options"))?;
    validate_test_scopes(table.get("test_scopes"))?;
    if let Some(value) = table.get("test_layout") {
        if analyzer == AnalyzerId::Python {
            return Err(
                "Config key test_layout is supported only by TypeScript and Svelte analyzers."
                    .to_owned(),
            );
        }
        if !matches!(value.as_str(), Some("mirrored" | "colocated")) {
            return Err("Config key test_layout must be 'mirrored' or 'colocated'.".to_owned());
        }
    }
    for name in ["select", "warn", "ignore"] {
        validate_selectors(table.get(name), name)?;
    }
    for name in [
        "tests",
        "tooling",
        "generated",
        "select",
        "warn",
        "ignore",
        "rule_paths",
        "rule_modules",
        "rule_packs",
    ] {
        if let Some(value) = table.get(name) {
            let _ = required_strings(Some(value), name)?;
        }
    }
    if let Some(value) = table.get("generated") {
        for pattern in required_strings(Some(value), "generated")? {
            validate_path_pattern(&pattern, "Generated path")?;
        }
    }
    validate_rule_packs(table.get("rule_packs"))?;
    let roots = required_strings(table.get("roots"), "roots")?;
    if roots.is_empty() {
        return Err("Config must define at least one root in roots.".to_owned());
    }
    validate_nested_roots(roots.clone())?;
    validate_boolean_table(table, "cache", &["enabled", "require_cacheable"])?;
    validate_threshold_table(table.get("thresholds"), "thresholds", false)?;
    validate_roles(table.get("roles"))?;
    validate_contracts(table.get("contracts"))?;
    if let Some(value) = table.get("framework") {
        if value.as_str() != Some("sveltekit") {
            return Err("Config key framework must be 'sveltekit'.".to_owned());
        }
        if analyzer != AnalyzerId::Svelte {
            return Err(
                "Config key framework is supported only by the Svelte analyzer.".to_owned(),
            );
        }
    }
    for name in ["shadcn", "openapi"] {
        if let Some(value) = table.get(name) {
            let path = value
                .as_str()
                .filter(|path| !path.trim().is_empty())
                .ok_or_else(|| format!("Config key {name} must be a non-empty string."))?;
            if !portable_target_path(path) {
                return Err(format!(
                    "Config key {name} must be a repository-relative path."
                ));
            }
        }
    }
    if let Some(value) = table.get("ui_kit") {
        let path = value
            .as_str()
            .filter(|path| !path.trim().is_empty())
            .ok_or_else(|| "Config key ui_kit must be a non-empty string.".to_owned())?;
        if !portable_target_path(path) {
            return Err("Config key ui_kit must be a repository-relative path.".to_owned());
        }
        if !roots
            .iter()
            .any(|root| path.starts_with(&format!("{root}/")))
        {
            return Err("Config key ui_kit must be beneath a configured root.".to_owned());
        }
    }
    validate_threshold_overrides(table.get("threshold_overrides"))?;
    exceptions::validate(table.get("rule_exceptions"), analyzer)?;
    validate_rule_ignores(table.get("rule_ignores"))?;
    validate_evaluation(table.get("evaluation"))?;
    Ok(())
}

fn portable_target_path(path: &str) -> bool {
    let bytes = path.as_bytes();
    !path.starts_with(['/', '\\'])
        && !path.contains('\\')
        && !(bytes.first().is_some_and(u8::is_ascii_alphabetic) && bytes.get(1) == Some(&b':'))
        && !path.split('/').any(|part| matches!(part, "" | "." | ".."))
}

pub(crate) fn select_target(
    table: &toml::map::Map<String, toml::Value>,
    target: Option<&str>,
) -> Result<TargetSelection, String> {
    if !table.contains_key(CONFIG_TARGETS_KEY) {
        if let Some(name) = target {
            return Err(format!("Unknown target name: {name}."));
        }
        return Ok(TargetSelection {
            table: table.clone(),
            target: None,
            analyzer: AnalyzerId::Python,
            root: DEFAULT_TARGET_ROOT.to_owned(),
        });
    }
    let mut validated = validated_targets(table)?;
    let selected_name = match target {
        Some(name) if validated.contains_key(name) => name.to_owned(),
        Some(name) => return Err(format!("Unknown target name: {name}.")),
        None if validated.len() == 1 => validated.keys().next().cloned().ok_or_else(|| {
            "Config key targets must define at least one named target.".to_owned()
        })?,
        None => {
            return Err(
                "Multiple targets are configured; select one with --target TARGET.".to_owned(),
            );
        }
    };
    let (selected, analyzer, root) = validated
        .remove(&selected_name)
        .ok_or_else(|| format!("Unknown target name: {selected_name}."))?;
    Ok(TargetSelection {
        table: selected,
        target: Some(selected_name),
        analyzer,
        root,
    })
}

pub(crate) fn selected_target_names(
    table: &toml::map::Map<String, toml::Value>,
    target: Option<&str>,
) -> Result<Vec<Option<String>>, String> {
    if !table.contains_key(CONFIG_TARGETS_KEY) {
        if let Some(name) = target {
            return Err(format!("Unknown target name: {name}."));
        }
        validate(table)?;
        return Ok(vec![None]);
    }
    let validated = validated_targets(table)?;
    if let Some(name) = target {
        if !validated.contains_key(name) {
            return Err(format!("Unknown target name: {name}."));
        }
        return Ok(vec![Some(name.to_owned())]);
    }
    let mut names = validated.keys().cloned().map(Some).collect::<Vec<_>>();
    names.sort();
    Ok(names)
}

pub(crate) fn validate_without_selection(
    table: &toml::map::Map<String, toml::Value>,
) -> Result<(), String> {
    if table.contains_key(CONFIG_TARGETS_KEY) {
        let _ = validated_targets(table)?;
        return Ok(());
    }
    validate(table)
}

fn validated_targets(
    table: &toml::map::Map<String, toml::Value>,
) -> Result<ValidatedTargets, String> {
    let mut mixed = table
        .keys()
        .filter(|key| key.as_str() != CONFIG_TARGETS_KEY)
        .cloned()
        .collect::<Vec<_>>();
    if !mixed.is_empty() {
        mixed.sort();
        return Err(format!(
            "Explicit targets cannot be mixed with legacy top-level config keys: {}.",
            mixed.join(", ")
        ));
    }
    let targets = table
        .get(CONFIG_TARGETS_KEY)
        .and_then(toml::Value::as_table)
        .ok_or_else(|| "Config key targets must be a table of named targets.".to_owned())?;
    if targets.is_empty() {
        return Err("Config key targets must define at least one named target.".to_owned());
    }
    let mut validated: ValidatedTargets = HashMap::new();
    let mut target_entries = targets.iter().collect::<Vec<_>>();
    target_entries.sort_by_key(|(name, _)| *name);
    for (name, value) in target_entries {
        if name.is_empty() {
            return Err("Target names must be non-empty strings.".to_owned());
        }
        let values = value
            .as_table()
            .ok_or_else(|| format!("Config target {name} must be a table."))?;
        let mut unknown = values
            .keys()
            .filter(|key| {
                !CONFIG_KEYS.contains(&key.as_str()) && !matches!(key.as_str(), "analyzer" | "root")
            })
            .cloned()
            .collect::<Vec<_>>();
        if !unknown.is_empty() {
            unknown.sort();
            return Err(format!(
                "Unknown targets.{name} config key(s): {}.",
                unknown.join(", ")
            ));
        }
        let analyzer = values
            .get("analyzer")
            .and_then(toml::Value::as_str)
            .filter(|value| !value.is_empty())
            .ok_or_else(|| {
                format!("Config key targets.{name}.analyzer must be a non-empty string.")
            })?;
        let analyzer = AnalyzerId::from_str(analyzer)
            .map_err(|_| format!("Unknown analyzer for target {name}: {analyzer}."))?;
        let root_value = match values.get("root") {
            None => DEFAULT_TARGET_ROOT,
            Some(value) => value
                .as_str()
                .filter(|text| !text.is_empty())
                .ok_or_else(|| {
                    format!("Config key targets.{name}.root must be a non-empty string.")
                })?,
        };
        let root = normalize_target_root(name, root_value)?;
        let mut selected = values.clone();
        selected.remove("analyzer");
        selected.remove("root");
        let selected = normalize_web_aliases(selected, analyzer)?;
        validate_for_analyzer(&selected, analyzer)?;
        validated.insert(name.clone(), (selected, analyzer, root));
    }
    Ok(validated)
}

fn normalize_web_aliases(
    mut table: toml::map::Map<String, toml::Value>,
    analyzer: AnalyzerId,
) -> Result<toml::map::Map<String, toml::Value>, String> {
    if analyzer == AnalyzerId::Python {
        return Ok(table);
    }
    if let Some(value) = table.remove("thresholds") {
        let normalized = match value {
            toml::Value::Table(values) => {
                toml::Value::Table(normalize_web_threshold_table(values, "thresholds")?)
            }
            other => other,
        };
        table.insert("thresholds".to_owned(), normalized);
    }
    if let Some(value) = table.remove("roles") {
        let normalized = match value {
            toml::Value::Table(mut roles) => {
                for (role, value) in &mut roles {
                    if let toml::Value::Table(values) = value {
                        *values = normalize_web_threshold_table(
                            std::mem::take(values),
                            &format!("roles.{role}"),
                        )?;
                    }
                }
                toml::Value::Table(roles)
            }
            other => other,
        };
        table.insert("roles".to_owned(), normalized);
    }
    if let Some(value) = table.remove("threshold_overrides") {
        let normalized = match value {
            toml::Value::Array(mut overrides) => {
                for entry in &mut overrides {
                    let Some(values) = entry
                        .as_table_mut()
                        .and_then(|item| item.get_mut("thresholds"))
                    else {
                        continue;
                    };
                    if let toml::Value::Table(thresholds) = values {
                        *thresholds = normalize_web_threshold_table(
                            std::mem::take(thresholds),
                            "threshold_overrides.thresholds",
                        )?;
                    }
                }
                toml::Value::Array(overrides)
            }
            other => other,
        };
        table.insert("threshold_overrides".to_owned(), normalized);
    }
    Ok(table)
}

fn normalize_web_threshold_table(
    mut values: toml::map::Map<String, toml::Value>,
    owner: &str,
) -> Result<toml::map::Map<String, toml::Value>, String> {
    for (alias, canonical) in WEB_THRESHOLD_ALIASES {
        let Some(alias_value) = values.get(*alias).cloned() else {
            continue;
        };
        if values
            .get(*canonical)
            .is_some_and(|canonical_value| canonical_value != &alias_value)
        {
            return Err(format!(
                "Conflicting threshold values in {owner}: {alias} and {canonical}."
            ));
        }
        values.insert((*canonical).to_owned(), alias_value);
        values.remove(*alias);
    }
    Ok(values)
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
            if !valid_selector(&selector) {
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

fn validate_selectors(value: Option<&toml::Value>, name: &str) -> Result<(), String> {
    let Some(value) = value else {
        return Ok(());
    };
    for selector in required_strings(Some(value), name)? {
        if !valid_selector(&selector) {
            return Err(format!(
                "Config key {name} contains invalid selector {selector}."
            ));
        }
    }
    Ok(())
}

fn validate_evaluation(value: Option<&toml::Value>) -> Result<(), String> {
    let Some(value) = value else {
        return Ok(());
    };
    let table = value
        .as_table()
        .ok_or_else(|| "Config key evaluation must be a table.".to_owned())?;
    for name in [EVALUATION_INCLUDE, "exclude"] {
        let Some(value) = table.get(name) else {
            continue;
        };
        let patterns = required_strings(Some(value), &format!("evaluation.{name}"))?;
        if name == EVALUATION_INCLUDE && patterns.is_empty() {
            return Err(format!("Config key evaluation.{name} must not be empty."));
        }
        for pattern in patterns {
            validate_path_pattern(&pattern, &format!("Evaluation {name}"))?;
        }
    }
    Ok(())
}

fn validate_path_pattern(pattern: &str, owner: &str) -> Result<(), String> {
    let expanded = expand_path_pattern(pattern)?;
    for candidate in expanded {
        let malformed = candidate.starts_with('/')
            || candidate.ends_with('/')
            || candidate.contains("//")
            || candidate.contains('\\')
            || candidate.contains(['?', '[', ']'])
            || candidate.split('/').any(|part| {
                matches!(part, "" | "." | "..")
                    || part.contains(RECURSIVE_GLOB) && part != RECURSIVE_GLOB
            })
            || candidate.contains("**/**");
        if malformed {
            return Err(format!(
                "{owner} must be a repository-relative POSIX glob: {pattern}."
            ));
        }
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
    let mut result: Vec<String> = Vec::new();
    for item in items {
        let text = item
            .as_str()
            .filter(|text| !text.is_empty())
            .ok_or_else(|| format!("Config key {name} must contain non-empty strings."))?;
        result.push(text.to_owned());
    }
    Ok(result)
}
