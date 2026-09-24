//! Validate the `[dupes]` configuration section.

use crate::dupes::_helpers::inputs::globs::GlobList;
use crate::dupes::constants::{
    CONFIG_ALLOWLIST_KEY, CONFIG_CONTRACTS_KEY, CONFIG_CONTRACT_KEY, CONFIG_DUPES_KEY,
    CONFIG_EXCLUDE_KEY, CONFIG_FORBIDDEN_OWNERS_KEY, CONFIG_PATHS_KEY, CONFIG_REASON_KEY,
};
use crate::dupes::models::{AllowlistEntry, ClassKey, ContractExemption, DupesConfig};

type Table = toml::map::Map<String, toml::Value>;

const SECTION_KEYS: &[&str] = &[
    CONFIG_EXCLUDE_KEY,
    CONFIG_ALLOWLIST_KEY,
    CONFIG_CONTRACTS_KEY,
];
const ALLOWLIST_KEYS: &[&str] = &[CONFIG_PATHS_KEY, CONFIG_REASON_KEY];
const CONTRACT_KEYS: &[&str] = &[
    CONFIG_CONTRACT_KEY,
    CONFIG_FORBIDDEN_OWNERS_KEY,
    CONFIG_PATHS_KEY,
    CONFIG_REASON_KEY,
];
const CLASS_SPEC_FORMAT: &str = "'relative/path.py:ClassName'";

/// Parse and validate an optional `[dupes]` table.
pub(crate) fn parse_dupes_config(value: Option<&toml::Value>) -> Result<DupesConfig, String> {
    let Some(value) = value else {
        return Ok(DupesConfig::default());
    };
    let table = value
        .as_table()
        .ok_or_else(|| format!("Config key {CONFIG_DUPES_KEY} must be a table."))?;
    reject_unknown(table, SECTION_KEYS, CONFIG_DUPES_KEY)?;
    let exclude = match table.get(CONFIG_EXCLUDE_KEY) {
        None => Vec::new(),
        Some(value) => glob_strings(value, &format!("{CONFIG_DUPES_KEY}.{CONFIG_EXCLUDE_KEY}"))?,
    };
    Ok(DupesConfig {
        exclude,
        allowlist: entries(table, CONFIG_ALLOWLIST_KEY, ALLOWLIST_KEYS)?
            .into_iter()
            .map(|(label, entry)| {
                reason(entry, &label)?;
                Ok(AllowlistEntry {
                    paths: required_globs(entry, &label)?,
                })
            })
            .collect::<Result<_, String>>()?,
        contract_exemptions: entries(table, CONFIG_CONTRACTS_KEY, CONTRACT_KEYS)?
            .into_iter()
            .map(|(label, entry)| contract_exemption(entry, &label))
            .collect::<Result<_, String>>()?,
    })
}

fn contract_exemption(entry: &Table, label: &str) -> Result<ContractExemption, String> {
    let contract = class_spec(
        entry.get(CONFIG_CONTRACT_KEY),
        &format!("{label} {CONFIG_CONTRACT_KEY}"),
    )?;
    let owners_label = format!("{label} {CONFIG_FORBIDDEN_OWNERS_KEY}");
    let forbidden_owners = match entry.get(CONFIG_FORBIDDEN_OWNERS_KEY) {
        None => Vec::new(),
        Some(toml::Value::Array(owners)) => owners
            .iter()
            .map(|owner| class_spec(Some(owner), &owners_label))
            .collect::<Result<_, String>>()?,
        Some(_) => {
            return Err(format!(
                "Config key {owners_label} must be a list of {CLASS_SPEC_FORMAT} strings."
            ))
        }
    };
    let paths = required_globs(entry, label)?;
    reason(entry, label)?;
    Ok(ContractExemption {
        contract,
        forbidden_owners,
        paths,
    })
}

fn entries<'t>(
    table: &'t Table,
    key: &str,
    allowed: &[&str],
) -> Result<Vec<(String, &'t Table)>, String> {
    let Some(value) = table.get(key) else {
        return Ok(Vec::new());
    };
    let items = value.as_array().ok_or_else(|| {
        format!("Config key {CONFIG_DUPES_KEY}.{key} must be an array of tables.")
    })?;
    items
        .iter()
        .enumerate()
        .map(|(position, item)| {
            let label = format!("{CONFIG_DUPES_KEY}.{key} entry {}", position + 1);
            let entry = item
                .as_table()
                .ok_or_else(|| format!("Config key {label} must be a table."))?;
            reject_unknown(entry, allowed, &label)?;
            Ok((label, entry))
        })
        .collect()
}

fn reject_unknown(table: &Table, allowed: &[&str], label: &str) -> Result<(), String> {
    let mut unknown: Vec<&str> = table
        .keys()
        .map(String::as_str)
        .filter(|key| !allowed.contains(key))
        .collect();
    if unknown.is_empty() {
        return Ok(());
    }
    unknown.sort_unstable();
    Err(format!(
        "Unknown {label} config key(s): {}.",
        unknown.join(", ")
    ))
}

fn required_globs(entry: &Table, label: &str) -> Result<Vec<String>, String> {
    let paths = entry
        .get(CONFIG_PATHS_KEY)
        .map(|value| glob_strings(value, &format!("{label} {CONFIG_PATHS_KEY}")))
        .transpose()?
        .unwrap_or_default();
    if paths.is_empty() {
        return Err(format!(
            "Config key {label} needs a non-empty {CONFIG_PATHS_KEY} list of path globs."
        ));
    }
    Ok(paths)
}

fn non_empty_text(value: &toml::Value) -> Option<String> {
    value
        .as_str()
        .map(str::trim)
        .filter(|text| !text.is_empty())
        .map(str::to_owned)
}

fn glob_strings(value: &toml::Value, label: &str) -> Result<Vec<String>, String> {
    let message = || format!("Config key {label} must be a list of non-empty path glob strings.");
    let paths = value
        .as_array()
        .ok_or_else(message)?
        .iter()
        .map(|item| non_empty_text(item).ok_or_else(message))
        .collect::<Result<Vec<_>, String>>()?;
    let _ = GlobList::new(&paths).map_err(|error| format!("Config key {label}: {error}"))?;
    Ok(paths)
}

/// Require the recorded justification every exemption must carry.
fn reason(entry: &Table, label: &str) -> Result<(), String> {
    entry
        .get(CONFIG_REASON_KEY)
        .and_then(toml::Value::as_str)
        .filter(|reason| !reason.trim().is_empty())
        .map(|_| ())
        .ok_or_else(|| format!("Config key {label} needs a non-empty {CONFIG_REASON_KEY}."))
}

fn class_spec(value: Option<&toml::Value>, label: &str) -> Result<ClassKey, String> {
    let invalid = || format!("Config key {label} must be {CLASS_SPEC_FORMAT}.");
    let (path, name) = value
        .and_then(toml::Value::as_str)
        .and_then(|text| text.split_once(':'))
        .ok_or_else(invalid)?;
    let identifier = name
        .chars()
        .next()
        .is_some_and(|first| first == '_' || first.is_alphabetic())
        && name
            .chars()
            .all(|character| character == '_' || character.is_alphanumeric());
    let relative = !path.starts_with('/')
        && !path.contains('\\')
        && path.split('/').all(|part| !matches!(part, "" | "." | ".."));
    if !path.ends_with(".py") || !relative || !identifier {
        return Err(invalid());
    }
    Ok(ClassKey {
        path: path.to_owned(),
        name: name.to_owned(),
    })
}
