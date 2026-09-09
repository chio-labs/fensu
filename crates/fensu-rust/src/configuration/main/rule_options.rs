//! Resolve Rust rule options from the shared Fensu configuration.

use crate::configuration::_helpers::option_values::apply_option;
use crate::models::RustPolicy;

/// Validate and resolve Rust-owned option tables.
pub fn resolve_rule_options(
    options: Option<&toml::map::Map<String, toml::Value>>,
) -> Result<RustPolicy, String> {
    let mut config = RustPolicy::default();
    if let Some(options) = options {
        for (code, value) in options {
            if !code.starts_with("FPRS") {
                continue;
            }
            let table = value
                .as_table()
                .ok_or_else(|| format!("Config key rule_options.{code} must be a table."))?;
            for (name, value) in table {
                config = apply_option(config, code, name, value)?;
            }
        }
    }
    config.validate()?;
    Ok(config)
}
