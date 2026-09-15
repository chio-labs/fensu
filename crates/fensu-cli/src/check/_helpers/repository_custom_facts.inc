//! Serialize Python facts needed by the cross-target repository-rule host.

use serde_json::{json, Value};

use crate::analyzer::AnalyzerId;
use crate::models::{ScopedSource, SourcePurpose};

pub(crate) const PYTHON_REPOSITORY_FACT_SCHEMA_VERSION: &str = "python-repository-facts-v1";

pub(crate) fn python_repository_fact_payload(sources: &[ScopedSource]) -> Value {
    json!({
        "schema_version": PYTHON_REPOSITORY_FACT_SCHEMA_VERSION,
        "parser_contract": AnalyzerId::Python.parser_contract(),
        "files": sources.iter().map(|source| json!({
            "path": source.target_path,
            "scope": source.scope,
            "scope_root": source.root_text,
            "relative_parts": source.relative_parts,
            "purpose": purpose(source.purpose),
            "source": String::from_utf8_lossy(&source.content),
        })).collect::<Vec<_>>(),
    })
}

fn purpose(value: SourcePurpose) -> &'static str {
    match value {
        SourcePurpose::Direct => "direct",
        SourcePurpose::Support => "support",
        SourcePurpose::Excluded => "excluded",
        SourcePurpose::Generated => "generated",
    }
}
