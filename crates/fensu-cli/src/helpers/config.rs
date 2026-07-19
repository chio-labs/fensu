use std::collections::HashMap;
use std::fs;
use std::path::{Path, PathBuf};

use crate::models::{Config, RuleException, ThresholdOverride};

const DEFAULT_THRESHOLDS: &[(&str, u32)] = &[
    ("max_statements", 40),
    ("max_distinct_calls", 20),
    ("max_locals", 20),
    ("max_file_lines", 2000),
    ("max_helpers_container_modules", 10),
    ("max_main_container_modules", 20),
    ("max_role_depth", 1),
    ("max_positional_args", 1),
    ("max_arguments", 10),
    ("max_statements_global", 70),
    ("max_script_entrypoint_lines", 80),
    ("min_shared_domain_prefix_packages", 2),
    ("min_custom_rule_test_cases", 1),
];

pub(crate) fn load(start: &Path) -> Result<(PathBuf, Config), String> {
    let (path, pyproject) = find(start)?;
    let raw =
        fs::read(&path).map_err(|error| format!("Could not read {}: {error}", path.display()))?;
    let document = toml::from_slice::<toml::Value>(&raw)
        .map_err(|error| format!("Could not parse {}: {error}", path.display()))?;
    let value = if pyproject {
        document
            .get("tool")
            .and_then(|value| value.get("fensu"))
            .ok_or_else(|| format!("{} does not contain [tool.fensu].", path.display()))?
    } else {
        &document
    };
    let table = value.as_table().ok_or_else(|| {
        format!(
            "Config source {} did not contain a TOML table.",
            path.display()
        )
    })?;
    let roots = strings(table.get("roots"));
    if roots.is_empty() {
        return Err("Config field roots must contain at least one path.".to_owned());
    }
    let mut thresholds = DEFAULT_THRESHOLDS
        .iter()
        .map(|(name, value)| ((*name).to_owned(), *value))
        .collect::<HashMap<_, _>>();
    thresholds.extend(numbers(table.get("thresholds")));
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
    if let Some(values) = table.get("contracts").and_then(toml::Value::as_table) {
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
    let cache = table.get("cache").and_then(toml::Value::as_table);
    let evaluation = table.get("evaluation").and_then(toml::Value::as_table);
    let experimental = table.get("experimental").and_then(toml::Value::as_table);
    Ok((
        path,
        Config {
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
            memory_enabled: experimental
                .and_then(|values| values.get("memory"))
                .and_then(toml::Value::as_bool)
                .unwrap_or(false),
            raw,
        },
    ))
}

pub(crate) fn custom_rules_are_configured(start: &Path) -> Result<bool, String> {
    let (_, config) = load(start)?;
    Ok(!config.rule_paths.is_empty() || !config.rule_modules.is_empty())
}

fn find(start: &Path) -> Result<(PathBuf, bool), String> {
    let resolved = start.canonicalize().map_err(|error| error.to_string())?;
    for directory in resolved.ancestors() {
        let fensu = directory.join("fensu.toml");
        if fensu.is_file() {
            return Ok((fensu, false));
        }
        let pyproject = directory.join("pyproject.toml");
        if pyproject.is_file() {
            let text = fs::read_to_string(&pyproject).unwrap_or_default();
            if text.contains("[tool.fensu]") {
                return Ok((pyproject, true));
            }
        }
    }
    Err("Could not find fensu.toml or [tool.fensu] in pyproject.toml.".to_owned())
}

fn strings(value: Option<&toml::Value>) -> Vec<String> {
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
                    reason: table
                        .get("reason")
                        .and_then(toml::Value::as_str)
                        .unwrap_or_default()
                        .to_owned(),
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

fn text(table: &toml::map::Map<String, toml::Value>, name: &str) -> String {
    table
        .get(name)
        .and_then(toml::Value::as_str)
        .unwrap_or_default()
        .to_owned()
}
