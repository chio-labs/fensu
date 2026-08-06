//! Decode and cache the compiled rule catalogue once per process.

use std::sync::OnceLock;

use crate::models::RuleMetadata;

static CATALOGUE: OnceLock<Vec<RuleMetadata>> = OnceLock::new();

pub(crate) fn rule_catalogue() -> &'static [RuleMetadata] {
    CATALOGUE
        .get_or_init(|| {
            let Ok(catalogue) =
                serde_json::from_slice(include_bytes!(concat!(env!("OUT_DIR"), "/catalogue.json")))
            else {
                return Vec::new();
            };
            catalogue
        })
        .as_slice()
}

pub(crate) fn rule_metadata(code: &str) -> Option<&'static RuleMetadata> {
    rule_catalogue().iter().find(|rule| rule.code == code)
}

pub(crate) fn configured_rule_catalogue(rule_packs: &[String]) -> Vec<&'static RuleMetadata> {
    rule_catalogue()
        .iter()
        .filter(|rule| {
            rule.pack
                .as_ref()
                .is_none_or(|pack| rule_packs.contains(pack))
        })
        .collect()
}
