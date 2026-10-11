use std::collections::HashSet;

#[allow(dead_code)]
#[path = "src/analyzer.rs"]
mod analyzer;
#[allow(dead_code)]
#[path = "src/catalogue/models.rs"]
mod catalogue_models;

use catalogue_models::RuleMetadata;

const RULE_FIELDS: &[&str] = &[
    "alias_of",
    "analyzers",
    "cacheable",
    "code",
    "configuration_inputs",
    "constraints",
    "contract_behaviors",
    "enabled_by_default",
    "execution_owner",
    "family",
    "implementation_code",
    "kind",
    "limits",
    "message",
    "options",
    "pack",
    "remediation",
    "severity",
    "slug",
    "source",
    "thresholds",
];

fn main() {
    let catalogue = include_bytes!("src/catalogue/data/catalogue.json");
    let typed_entries = serde_json::from_slice::<Vec<RuleMetadata>>(catalogue)
        .expect("every catalogue entry deserializes as complete RuleMetadata");
    assert!(!typed_entries.is_empty(), "catalogue asset is nonempty");
    let catalogue_value = serde_json::from_slice::<serde_json::Value>(catalogue)
        .expect("catalogue asset contains JSON");
    let entries = catalogue_value
        .as_array()
        .filter(|entries| !entries.is_empty())
        .expect("catalogue asset contains a nonempty array");
    let mut codes = HashSet::new();
    for (entry, typed) in entries.iter().zip(&typed_entries) {
        let code = typed.code.as_str();
        assert!(
            codes.insert(code),
            "catalogue contains duplicate code {code}"
        );
        let mut fields = entry
            .as_object()
            .expect("catalogue entry is an object")
            .keys()
            .map(String::as_str)
            .collect::<Vec<_>>();
        fields.sort_unstable();
        assert_eq!(
            fields, RULE_FIELDS,
            "catalogue entry {code} has incomplete schema"
        );
    }
    println!("cargo:rerun-if-changed=src/catalogue/data/catalogue.json");
}
