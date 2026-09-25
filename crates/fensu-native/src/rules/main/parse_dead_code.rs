//! Strict, opt-in Python reachability configuration.

use globset::Glob;

use crate::rules::types::NativeDeadCodeSettings;

pub fn parse_dead_code(value: &serde_json::Value) -> Result<NativeDeadCodeSettings, String> {
    if value.is_null() {
        return Ok((false, Vec::new()));
    }
    let table = value
        .as_object()
        .ok_or("Config key dead_code must be a table.")?;
    if table
        .keys()
        .any(|key| !matches!(key.as_str(), "enabled" | "roots"))
    {
        return Err("Unknown dead_code config key; expected enabled or roots.".to_owned());
    }
    let enabled = table
        .get("enabled")
        .map(|value| {
            value
                .as_bool()
                .ok_or("dead_code.enabled must be a boolean.")
        })
        .transpose()?
        .unwrap_or(false);
    let mut roots: Vec<(Vec<String>, Vec<String>, String)> = Vec::new();
    if let Some(value) = table.get("roots") {
        for entry in value
            .as_array()
            .ok_or("dead_code.roots must be an array of tables.")?
        {
            let entry = entry
                .as_object()
                .ok_or("Each dead_code.roots entry must be a table.")?;
            if entry
                .keys()
                .any(|key| !matches!(key.as_str(), "modules" | "symbols" | "reason"))
            {
                return Err(
                    "Unknown dead_code.roots key; expected modules, symbols and reason.".to_owned(),
                );
            }
            let modules = patterns(entry.get("modules"), "dead_code.roots.modules")?;
            let symbols = patterns(entry.get("symbols"), "dead_code.roots.symbols")?;
            let reason = entry
                .get("reason")
                .and_then(serde_json::Value::as_str)
                .filter(|value| !value.trim().is_empty())
                .ok_or("dead_code.roots.reason must be a non-empty string.")?;
            roots.push((modules, symbols, reason.to_owned()));
        }
    }
    Ok((enabled, roots))
}

fn patterns(value: Option<&serde_json::Value>, key: &str) -> Result<Vec<String>, String> {
    let values = value
        .and_then(serde_json::Value::as_array)
        .ok_or_else(|| format!("{key} must be an array of patterns."))?
        .iter()
        .map(|value| {
            value
                .as_str()
                .map(str::to_owned)
                .ok_or_else(|| format!("{key} must contain string patterns."))
        })
        .collect::<Result<Vec<_>, _>>()?;
    if values.is_empty() {
        return Err(format!("{key} must be a non-empty array of patterns."));
    }
    for value in &values {
        if value.trim().is_empty() || value.contains(['/', '\\']) {
            return Err(format!(
                "{key} must contain dotted module or symbol patterns, not file paths."
            ));
        }
        Glob::new(value).map_err(|error| format!("Invalid {key} pattern: {error}"))?;
    }
    Ok(values)
}
