//! Decode and cache the compiled rule catalogue once per process.

use std::sync::OnceLock;

use crate::catalogue::models::RuleMetadata;

static CATALOGUE: OnceLock<Result<Vec<RuleMetadata>, String>> = OnceLock::new();

pub(crate) fn rule_catalogue() -> Result<&'static [RuleMetadata], String> {
    CATALOGUE
        .get_or_init(|| {
            serde_json::from_slice(include_bytes!(concat!(env!("OUT_DIR"), "/catalogue.json")))
                .map_err(|error| format!("Embedded rule catalogue is invalid: {error}"))
        })
        .as_ref()
        .map(Vec::as_slice)
        .map_err(Clone::clone)
}

pub(crate) fn rule_metadata(code: &str) -> Result<Option<&'static RuleMetadata>, String> {
    Ok(rule_catalogue()?.iter().find(|rule| rule.code == code))
}

pub(crate) fn configured_rule_catalogue(
    rule_packs: &[String],
) -> Result<Vec<&'static RuleMetadata>, String> {
    Ok(rule_catalogue()?
        .iter()
        .filter(|rule| {
            rule.pack
                .as_ref()
                .is_none_or(|pack| rule_packs.contains(pack))
        })
        .collect())
}
