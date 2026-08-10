use std::collections::HashMap;

use crate::configuration::_helpers::validation::required_strings;
use crate::configuration::constants::{
    DEFAULT_CACHE_ENABLED, DEFAULT_CACHE_REQUIRE_CACHEABLE, DEFAULT_CONTRACTS, DEFAULT_IGNORE,
    DEFAULT_SELECT, DEFAULT_TEST_PATHS, DEFAULT_TEST_SCOPES, DEFAULT_THRESHOLDS, DEFAULT_WARN,
    WEB_DEFAULT_CONTRACTS,
};
use crate::models::{Config, RuleException, RuleIgnore, TargetSelection, ThresholdOverride};

pub(crate) fn build(
    selection: TargetSelection,
    raw: Vec<u8>,
    pyproject: bool,
) -> Result<Config, String> {
    let table = &selection.table;
    let roots = required_strings(table.get("roots"), "roots")?;
    if roots.is_empty() {
        return Err("Config must define at least one root in roots.".to_owned());
    }
    let mut thresholds = DEFAULT_THRESHOLDS
        .iter()
        .map(|(name, value)| ((*name).to_owned(), *value))
        .collect::<HashMap<_, _>>();
    thresholds.extend(numbers(table.get("thresholds")));
    let contracts = contracts(table.get("contracts"), selection.analyzer);
    let cache = table.get("cache").and_then(toml::Value::as_table);
    let evaluation = table.get("evaluation").and_then(toml::Value::as_table);
    Ok(Config {
        analyzer: selection.analyzer,
        target: selection.target,
        target_root: selection.root,
        roots,
        tests: strings_or(table.get("tests"), DEFAULT_TEST_PATHS),
        test_scopes: strings_or(table.get("test_scopes"), DEFAULT_TEST_SCOPES),
        tooling: strings(table.get("tooling")),
        generated: strings(table.get("generated")),
        select: strings_or(
            table.get("select"),
            if selection.analyzer == crate::analyzer::AnalyzerId::Python {
                DEFAULT_SELECT
            } else {
                &["FW"]
            },
        ),
        warn: strings_or(table.get("warn"), DEFAULT_WARN),
        ignore: strings_or(table.get("ignore"), DEFAULT_IGNORE),
        rule_paths: strings(table.get("rule_paths")),
        rule_modules: strings(table.get("rule_modules")),
        rule_packs: strings(table.get("rule_packs")),
        rule_options: table
            .get("rule_options")
            .and_then(toml::Value::as_table)
            .cloned()
            .unwrap_or_default(),
        cache_enabled: cache
            .and_then(|values| values.get("enabled"))
            .and_then(toml::Value::as_bool)
            .unwrap_or(DEFAULT_CACHE_ENABLED),
        cache_require_cacheable: cache
            .and_then(|values| values.get("require_cacheable"))
            .and_then(toml::Value::as_bool)
            .unwrap_or(DEFAULT_CACHE_REQUIRE_CACHEABLE),
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
        ui_kit: table
            .get("ui_kit")
            .and_then(toml::Value::as_str)
            .map(|value| value.trim_end_matches('/').to_owned()),
        framework: table
            .get("framework")
            .and_then(toml::Value::as_str)
            .map(str::to_owned)
            .or_else(|| {
                (selection.analyzer == crate::analyzer::AnalyzerId::Svelte)
                    .then(|| "sveltekit".to_owned())
            }),
        shadcn: table
            .get("shadcn")
            .and_then(toml::Value::as_str)
            .map(str::to_owned),
        openapi: table
            .get("openapi")
            .and_then(toml::Value::as_str)
            .map(str::to_owned),
        exceptions: exceptions(table.get("rule_exceptions")),
        rule_ignores: rule_ignores(table.get("rule_ignores")),
        skills_name: skills_name(table)?,
        source_kind: if pyproject { "pyproject" } else { "fensu_toml" }.to_owned(),
        raw,
    })
}

fn contracts(
    value: Option<&toml::Value>,
    analyzer: crate::analyzer::AnalyzerId,
) -> Vec<(String, String)> {
    let mut contracts = DEFAULT_CONTRACTS
        .iter()
        .map(|(pattern, behavior)| ((*pattern).to_owned(), (*behavior).to_owned()))
        .collect::<Vec<_>>();
    if analyzer != crate::analyzer::AnalyzerId::Python {
        contracts.extend(
            WEB_DEFAULT_CONTRACTS
                .iter()
                .map(|(pattern, behavior)| ((*pattern).to_owned(), (*behavior).to_owned())),
        );
    }
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
    let mut numbers: HashMap<String, u32> = HashMap::new();
    let Some(values) = value.and_then(toml::Value::as_table) else {
        return numbers;
    };
    for (name, value) in values {
        let Some(number) = value.as_integer() else {
            continue;
        };
        if let Ok(number) = u32::try_from(number) {
            numbers.insert(name.clone(), number);
        }
    }
    numbers
}

fn role_thresholds(value: Option<&toml::Value>) -> HashMap<String, HashMap<String, u32>> {
    let mut thresholds: HashMap<String, HashMap<String, u32>> = HashMap::new();
    if let Some(values) = value.and_then(toml::Value::as_table) {
        for (name, value) in values {
            thresholds.insert(name.clone(), numbers(Some(value)));
        }
    }
    thresholds
}

fn threshold_overrides(value: Option<&toml::Value>) -> Vec<ThresholdOverride> {
    let mut overrides: Vec<ThresholdOverride> = Vec::new();
    let Some(items) = value.and_then(toml::Value::as_array) else {
        return overrides;
    };
    for table in items.iter().filter_map(toml::Value::as_table) {
        overrides.push(ThresholdOverride {
            paths: strings(table.get("paths")),
            thresholds: numbers(table.get("thresholds")),
            reason: text(table, "reason"),
        });
    }
    overrides
}

fn exceptions(value: Option<&toml::Value>) -> Vec<RuleException> {
    let mut exceptions: Vec<RuleException> = Vec::new();
    let Some(items) = value.and_then(toml::Value::as_array) else {
        return exceptions;
    };
    for table in items.iter().filter_map(toml::Value::as_table) {
        exceptions.push(RuleException {
            rule: text(table, "rule"),
            path: text(table, "path"),
            reason: text(table, "reason"),
            symbols: strings(table.get("symbols")),
        });
    }
    exceptions
}

fn rule_ignores(value: Option<&toml::Value>) -> Vec<RuleIgnore> {
    let mut ignores: Vec<RuleIgnore> = Vec::new();
    let Some(items) = value.and_then(toml::Value::as_array) else {
        return ignores;
    };
    for table in items.iter().filter_map(toml::Value::as_table) {
        ignores.push(RuleIgnore {
            rules: strings(table.get("rules")),
            paths: strings(table.get("paths")),
            reason: text(table, "reason"),
        });
    }
    ignores
}

fn text(table: &toml::map::Map<String, toml::Value>, name: &str) -> String {
    table
        .get(name)
        .and_then(toml::Value::as_str)
        .unwrap_or_default()
        .to_owned()
}
