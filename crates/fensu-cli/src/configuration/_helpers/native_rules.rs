use std::collections::HashSet;

use crate::analyzer::AnalyzerId;
use crate::configuration::_helpers::validation::required_strings;

const APPROVED_LOADER_BOUNDARIES: &str = "approved_loader_boundaries";
const APPROVED_LOADER_BOUNDARIES_KEY: &str = "rule_options.FPDG022.approved_loader_boundaries";
const DAGSTER_AUTOLOAD_CODE: &str = "FPDG022";
const DAGSTER_PACK: &str = "dagster";
const RUST_PACK: &str = "rust";
const SVELTEKIT_PACK: &str = "sveltekit";
const TYPESCRIPT_PACK: &str = "typescript";

pub(crate) fn validate_rule_packs(value: Option<&toml::Value>) -> Result<(), String> {
    let Some(value) = value else {
        return Ok(());
    };
    let packs = required_strings(Some(value), "rule_packs")?;
    let mut seen: HashSet<&str> = HashSet::new();
    for pack in &packs {
        if !matches!(
            pack.as_str(),
            DAGSTER_PACK | RUST_PACK | SVELTEKIT_PACK | TYPESCRIPT_PACK
        ) {
            return Err(format!("Unknown native rule pack: {pack}."));
        }
        if !seen.insert(pack) {
            return Err("Config key rule_packs must not contain duplicates.".to_owned());
        }
    }
    Ok(())
}

pub(crate) fn validate_rule_options(
    value: Option<&toml::Value>,
    analyzer: AnalyzerId,
) -> Result<(), String> {
    let Some(value) = value else {
        return Ok(());
    };
    let rules = value
        .as_table()
        .ok_or_else(|| "Config key rule_options must be a table.".to_owned())?;
    if rules.values().any(|options| !options.is_table()) {
        return Err("Config key rule_options must contain rule-code tables.".to_owned());
    }
    let _ = fensu_rust::configuration::main::rule_options::resolve_rule_options(Some(rules))?;
    let rust_catalogue =
        crate::catalogue::main::rule_catalogue::configured_rule_catalogue(&[RUST_PACK.to_owned()])?;
    for (code, options) in rules {
        if code.starts_with('X') {
            continue;
        }
        if analyzer == AnalyzerId::Rust && !code.starts_with("FPRS") {
            return Err(format!(
                "Rule options for {code} are not supported by the Rust analyzer."
            ));
        }
        if code.starts_with("FPRS") {
            if analyzer != AnalyzerId::Rust {
                return Err(format!(
                    "Rule options for {code} are supported only by the Rust analyzer."
                ));
            }
            if !rust_catalogue.iter().any(|rule| rule.code == *code) {
                return Err(format!("Unknown native rule options code: {code}."));
            }
            continue;
        }
        if code != DAGSTER_AUTOLOAD_CODE {
            return Err(format!("Unknown native rule options code: {code}."));
        }
        let table = options
            .as_table()
            .ok_or_else(|| "Config key rule_options must contain rule-code tables.".to_owned())?;
        for (name, option_value) in table {
            if name != APPROVED_LOADER_BOUNDARIES {
                return Err(format!("Rule FPDG022 does not declare option {name}."));
            }
            let _ = required_strings(Some(option_value), APPROVED_LOADER_BOUNDARIES_KEY)?;
        }
    }
    Ok(())
}
