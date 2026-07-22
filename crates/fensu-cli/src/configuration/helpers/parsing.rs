use std::collections::HashMap;

use crate::configuration::helpers::validation::{required_strings, validate_keys};
use crate::constants::{DEFAULT_MEMORY_ARCHIVE_DAYS, DEFAULT_THRESHOLDS};
use crate::models::{Config, RuleException, RuleIgnore, ThresholdOverride};

pub(crate) fn build(
    table: &toml::map::Map<String, toml::Value>,
    raw: Vec<u8>,
    pyproject: bool,
) -> Result<Config, String> {
    let roots = required_strings(table.get("roots"), "roots")?;
    if roots.is_empty() {
        return Err("Config must define at least one root in roots.".to_owned());
    }
    let mut thresholds = DEFAULT_THRESHOLDS
        .iter()
        .map(|(name, value)| ((*name).to_owned(), *value))
        .collect::<HashMap<_, _>>();
    thresholds.extend(numbers(table.get("thresholds")));
    let contracts = contracts(table.get("contracts"));
    let cache = table.get("cache").and_then(toml::Value::as_table);
    let evaluation = table.get("evaluation").and_then(toml::Value::as_table);
    Ok(Config {
        roots,
        tests: strings_or(table.get("tests"), &["tests"]),
        tooling: strings(table.get("tooling")),
        select: strings_or(table.get("select"), &["FF"]),
        warn: strings(table.get("warn")),
        ignore: strings(table.get("ignore")),
        rule_paths: strings(table.get("rule_paths")),
        rule_modules: strings(table.get("rule_modules")),
        cache_enabled: cache
            .and_then(|values| values.get("enabled"))
            .and_then(toml::Value::as_bool)
            .unwrap_or(true),
        cache_require_cacheable: cache
            .and_then(|values| values.get("require_cacheable"))
            .and_then(toml::Value::as_bool)
            .unwrap_or(false),
        evaluation_include: evaluation
            .map(|values| strings(values.get("include")))
            .unwrap_or_default(),
        evaluation_exclude: evaluation
            .map(|values| strings(values.get("exclude")))
            .unwrap_or_default(),
        thresholds,
        role_thresholds: role_thresholds(table.get("roles")),
        threshold_overrides: threshold_overrides(table.get("threshold_overrides")),
        contracts,
        exceptions: exceptions(table.get("rule_exceptions")),
        rule_ignores: rule_ignores(table.get("rule_ignores")),
        memory_enabled: memory_enabled(table)?,
        memory_archive_after_days: memory_archive_after_days(table)?,
        skills_name: skills_name(table)?,
        source_kind: if pyproject { "pyproject" } else { "fensu_toml" }.to_owned(),
        raw,
    })
}

fn contracts(value: Option<&toml::Value>) -> Vec<(String, String)> {
    let mut contracts = vec![
        ("validate_*".to_owned(), "no-return".to_owned()),
        ("enforce_*".to_owned(), "no-return".to_owned()),
        ("is_*".to_owned(), "returns-bool".to_owned()),
        ("has_*".to_owned(), "returns-bool".to_owned()),
        ("can_*".to_owned(), "returns-bool".to_owned()),
        ("supports_*".to_owned(), "returns-bool".to_owned()),
        ("get_*".to_owned(), "returns-value".to_owned()),
        ("to_*".to_owned(), "returns-value".to_owned()),
        ("as_*".to_owned(), "returns-value".to_owned()),
        ("iter_*".to_owned(), "returns-iterator".to_owned()),
    ];
    if let Some(values) = value.and_then(toml::Value::as_table) {
        for (name, value) in values {
            if let Some(text) = value.as_str() {
                if let Some(existing) = contracts.iter_mut().find(|(pattern, _)| pattern == name) {
                    existing.1 = text.to_owned();
                } else {
                    contracts.push((name.clone(), text.to_owned()));
                }
            }
        }
    }
    contracts
}

fn skills_name(table: &toml::map::Map<String, toml::Value>) -> Result<Option<String>, String> {
    let Some(skills) = table.get("skills") else {
        return Ok(None);
    };
    let values = skills
        .as_table()
        .ok_or_else(|| "Config key skills must be a table.".to_owned())?;
    values
        .get("name")
        .and_then(toml::Value::as_str)
        .filter(|value| !value.trim().is_empty())
        .map(str::to_owned)
        .map(Some)
        .ok_or_else(|| "Config key skills.name must be a non-empty string.".to_owned())
}

fn memory_archive_after_days(table: &toml::map::Map<String, toml::Value>) -> Result<u64, String> {
    let Some(memory_value) = table.get("memory") else {
        return Ok(DEFAULT_MEMORY_ARCHIVE_DAYS);
    };
    let memory = memory_value
        .as_table()
        .ok_or_else(|| "Config key memory must be a table.".to_owned())?;
    validate_keys(memory, &["tasks"], "memory")?;
    let Some(tasks_value) = memory.get("tasks") else {
        return Ok(DEFAULT_MEMORY_ARCHIVE_DAYS);
    };
    let tasks = tasks_value
        .as_table()
        .ok_or_else(|| "Config key memory.tasks must be a table.".to_owned())?;
    validate_keys(tasks, &["archive_after_days"], "memory.tasks")?;
    let Some(value) = tasks.get("archive_after_days") else {
        return Ok(DEFAULT_MEMORY_ARCHIVE_DAYS);
    };
    let Some(days) = value.as_integer() else {
        return Err("Config key memory.tasks.archive_after_days must be an integer.".to_owned());
    };
    u64::try_from(days)
        .map_err(|_| "Config key memory.tasks.archive_after_days must be non-negative.".to_owned())
}

fn memory_enabled(table: &toml::map::Map<String, toml::Value>) -> Result<bool, String> {
    let Some(experimental_value) = table.get("experimental") else {
        return Ok(false);
    };
    let experimental = experimental_value
        .as_table()
        .ok_or_else(|| "Config key experimental must be a table.".to_owned())?;
    validate_keys(experimental, &["memory"], "experimental")?;
    let Some(value) = experimental.get("memory") else {
        return Ok(false);
    };
    value
        .as_bool()
        .ok_or_else(|| "Config key experimental.memory must be a boolean.".to_owned())
}

pub(crate) fn strings(value: Option<&toml::Value>) -> Vec<String> {
    value
        .and_then(toml::Value::as_array)
        .map(|items| {
            items
                .iter()
                .filter_map(toml::Value::as_str)
                .map(str::to_owned)
                .collect()
        })
        .unwrap_or_default()
}

fn strings_or(value: Option<&toml::Value>, default: &[&str]) -> Vec<String> {
    value.map_or_else(
        || default.iter().map(|item| (*item).to_owned()).collect(),
        |item| strings(Some(item)),
    )
}

fn numbers(value: Option<&toml::Value>) -> HashMap<String, u32> {
    value
        .and_then(toml::Value::as_table)
        .map(|values| {
            values
                .iter()
                .filter_map(|(name, value)| {
                    value
                        .as_integer()
                        .and_then(|number| u32::try_from(number).ok())
                        .map(|number| (name.clone(), number))
                })
                .collect()
        })
        .unwrap_or_default()
}

fn role_thresholds(value: Option<&toml::Value>) -> HashMap<String, HashMap<String, u32>> {
    value
        .and_then(toml::Value::as_table)
        .map(|values| {
            values
                .iter()
                .map(|(name, value)| (name.clone(), numbers(Some(value))))
                .collect()
        })
        .unwrap_or_default()
}

fn threshold_overrides(value: Option<&toml::Value>) -> Vec<ThresholdOverride> {
    value
        .and_then(toml::Value::as_array)
        .map(|items| {
            items
                .iter()
                .filter_map(toml::Value::as_table)
                .map(|table| ThresholdOverride {
                    paths: strings(table.get("paths")),
                    thresholds: numbers(table.get("thresholds")),
                    reason: text(table, "reason"),
                })
                .collect()
        })
        .unwrap_or_default()
}

fn exceptions(value: Option<&toml::Value>) -> Vec<RuleException> {
    value
        .and_then(toml::Value::as_array)
        .map(|items| {
            items
                .iter()
                .filter_map(toml::Value::as_table)
                .map(|table| RuleException {
                    rule: text(table, "rule"),
                    path: text(table, "path"),
                    reason: text(table, "reason"),
                    symbols: strings(table.get("symbols")),
                })
                .collect()
        })
        .unwrap_or_default()
}

fn rule_ignores(value: Option<&toml::Value>) -> Vec<RuleIgnore> {
    value
        .and_then(toml::Value::as_array)
        .map(|items| {
            items
                .iter()
                .filter_map(toml::Value::as_table)
                .map(|table| RuleIgnore {
                    rules: strings(table.get("rules")),
                    paths: strings(table.get("paths")),
                    reason: text(table, "reason"),
                })
                .collect()
        })
        .unwrap_or_default()
}

fn text(table: &toml::map::Map<String, toml::Value>, name: &str) -> String {
    table
        .get(name)
        .and_then(toml::Value::as_str)
        .unwrap_or_default()
        .to_owned()
}
