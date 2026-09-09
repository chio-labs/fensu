//! Resolve Rust rule options from the shared Fensu configuration.

use crate::models::RustPolicy;

pub(crate) fn apply_option(
    mut config: RustPolicy,
    code: &str,
    name: &str,
    value: &toml::Value,
) -> Result<RustPolicy, String> {
    let key = format!("rule_options.{code}.{name}");
    let thresholds = &mut config.repository.thresholds;
    match (code, name) {
        ("FPRSR601", "max_file_lines") => thresholds.max_file_lines = positive(value, &key)?,
        ("FPRSS010", "max_arguments") => thresholds.max_arguments = positive(value, &key)?,
        ("FPRSS011", "max_statements") => thresholds.max_statements_global = positive(value, &key)?,
        ("FPRSS001", "max_statements") => thresholds.max_statements_entry = positive(value, &key)?,
        ("FPRSS002", "max_distinct_calls") => {
            thresholds.max_distinct_calls_entry = positive(value, &key)?
        }
        ("FPRSS003", "max_locals") => thresholds.max_locals_entry = positive(value, &key)?,
        ("FPRSR301", "max_modules") => {
            thresholds.max_helper_container_modules = positive(value, &key)?
        }
        ("FPRSR302", "max_modules") => {
            thresholds.max_main_container_modules = positive(value, &key)?
        }
        ("FPRSL301", "forbidden_packages") => {
            config.tooling.runtime_forbidden_packages = strings(value, &key)?
        }
        ("FPRSL102", "packages") => config.raw_parser_boundary.packages = strings(value, &key)?,
        ("FPRSL102", "restricted_paths") => {
            config.raw_parser_boundary.restricted_paths = strings(value, &key)?
        }
        ("FPRSL102", "remediation") => config.raw_parser_boundary.remediation = text(value, &key)?,
        ("FPRSL304", "crate_names") => config.repository.crate_names = strings(value, &key)?,
        ("FPRSL305", "domain_paths") => config.repository.domain_paths = strings(value, &key)?,
        ("FPRSL305", "role_paths") => config.repository.role_paths = strings(value, &key)?,
        ("FPRSL305", "intentional_layout_paths") => {
            config.repository.intentional_layout_paths = strings(value, &key)?
        }
        _ => return Err(format!("Rule {code} does not declare option {name}.")),
    }
    Ok(config)
}

fn positive(value: &toml::Value, key: &str) -> Result<usize, String> {
    let number = value
        .as_integer()
        .filter(|value| *value > 0)
        .ok_or_else(|| format!("Config key {key} must be a positive integer."))?;
    usize::try_from(number)
        .map_err(|error| format!("Config key {key} exceeds the supported integer range: {error}."))
}

fn text(value: &toml::Value, key: &str) -> Result<String, String> {
    value
        .as_str()
        .filter(|value| !value.trim().is_empty())
        .map(str::to_owned)
        .ok_or_else(|| format!("Config key {key} must be a non-empty string."))
}

fn strings(value: &toml::Value, key: &str) -> Result<Vec<String>, String> {
    let values = value
        .as_array()
        .ok_or_else(|| format!("Config key {key} must be a string list."))?;
    let result = values
        .iter()
        .map(|value| text(value, key))
        .collect::<Result<Vec<_>, _>>()?;
    crate::configuration::_helpers::repository_policy::validate_non_empty_unique(&result, key)?;
    Ok(result)
}
