use std::collections::HashSet;

use crate::analyzer::AnalyzerId;
use crate::configuration::_helpers::selectors::valid_code;

const RULE_EXCEPTION_SYMBOLS: &str = "symbols";

pub(crate) fn validate(value: Option<&toml::Value>, analyzer: AnalyzerId) -> Result<(), String> {
    let Some(value) = value else {
        return Ok(());
    };
    let entries = value
        .as_array()
        .ok_or_else(|| "Config key rule_exceptions must be an array of tables.".to_owned())?;
    let mut seen: HashSet<(String, String, Option<String>)> = HashSet::new();
    for entry in entries {
        let table = entry
            .as_table()
            .ok_or_else(|| "Each rule_exceptions entry must be a table.".to_owned())?;
        let required = ["rule", "path", "reason"];
        if required.iter().any(|name| !table.contains_key(*name))
            || table
                .keys()
                .any(|name| !required.contains(&name.as_str()) && name != RULE_EXCEPTION_SYMBOLS)
        {
            return Err("Each rule_exceptions entry must define rule, path, and reason, with optional symbols.".to_owned());
        }
        let rule = exception_text(table, "rule")?;
        let path = exception_text(table, "path")?;
        let reason = exception_text(table, "reason")?;
        if reason.trim().is_empty() {
            return Err("Rule exception reason must be non-empty.".to_owned());
        }
        if !valid_code(&rule) {
            return Err(format!(
                "Rule exception must use one exact rule code: {rule}."
            ));
        }
        validate_path(&path, analyzer)?;
        let symbols = match table.get(RULE_EXCEPTION_SYMBOLS) {
            Some(value) => {
                super::validation::required_strings(Some(value), "rule_exceptions.symbols")?
            }
            None => Vec::new(),
        };
        if table.contains_key(RULE_EXCEPTION_SYMBOLS) && symbols.is_empty() {
            return Err("Rule exception symbols must not be empty; omit symbols for a file-level exception.".to_owned());
        }
        if symbols.is_empty() && !seen.insert((rule.clone(), path.clone(), None)) {
            return Err(format!(
                "Duplicate file-level rule exception for {rule} at {path}."
            ));
        }
        for symbol in symbols {
            if !valid_qualified_symbol(&symbol) {
                return Err(format!(
                    "Malformed qualified rule exception symbol: {symbol}."
                ));
            }
            if !seen.insert((rule.clone(), path.clone(), Some(symbol.clone()))) {
                return Err(format!(
                    "Duplicate rule exception for {rule} at {path}: {symbol}."
                ));
            }
        }
    }
    Ok(())
}

fn exception_text(
    table: &toml::map::Map<String, toml::Value>,
    name: &str,
) -> Result<String, String> {
    table
        .get(name)
        .and_then(toml::Value::as_str)
        .filter(|value| !value.is_empty())
        .map(str::to_owned)
        .ok_or_else(|| format!("Rule exception {name} must be a non-empty string."))
}

fn valid_qualified_symbol(value: &str) -> bool {
    let mut parts = value.split('.');
    let valid = |part: &str| {
        let mut characters = part.chars();
        characters
            .next()
            .is_some_and(|item| item.is_ascii_alphabetic() || item == '_')
            && characters.all(|item| item.is_ascii_alphanumeric() || item == '_')
    };
    let first = parts.next().is_some_and(valid);
    let second = parts.next();
    first && second.is_none_or(valid) && parts.next().is_none()
}

fn validate_path(path: &str, analyzer: AnalyzerId) -> Result<(), String> {
    let supported = match analyzer {
        AnalyzerId::Python => path.ends_with(".py"),
        AnalyzerId::Rust => path.ends_with(".rs") || path.ends_with("Cargo.toml"),
        AnalyzerId::TypeScript => web_source_path(path),
        AnalyzerId::Svelte => path.ends_with(".svelte") || web_source_path(path),
    };
    if path.starts_with('/')
        || path.contains('\\')
        || path.contains(['*', '?', '[', ']'])
        || path.split('/').any(|part| matches!(part, "" | "." | ".."))
        || !supported
    {
        let source = match analyzer {
            AnalyzerId::Python => "Python",
            AnalyzerId::Rust => "Rust",
            AnalyzerId::TypeScript => "TypeScript",
            AnalyzerId::Svelte => "Svelte",
        };
        return Err(format!("Rule exception path must be one exact repository-relative POSIX {source} source file: {path}."));
    }
    Ok(())
}

fn web_source_path(path: &str) -> bool {
    path.ends_with(".d.ts")
        || path.ends_with(".d.mts")
        || path.ends_with(".d.cts")
        || [".ts", ".tsx", ".mts", ".cts", ".js", ".jsx", ".mjs", ".cjs"]
            .iter()
            .any(|suffix| path.ends_with(suffix))
}
