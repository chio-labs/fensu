//! Parser-independent serialized Rust workspace facts.

use serde::{Deserialize, Serialize};

/// One stable source position using one-based lines and zero-based UTF-8 byte columns.
#[derive(Clone, Debug, Deserialize, Eq, Ord, PartialEq, PartialOrd, Serialize)]
#[serde(deny_unknown_fields)]
pub struct RustSourcePosition {
    pub line: usize,
    pub column: usize,
}

/// One end-exclusive source range in a repository-relative Rust file.
#[derive(Clone, Debug, Deserialize, Eq, Ord, PartialEq, PartialOrd, Serialize)]
#[serde(deny_unknown_fields)]
pub struct RustSourceRange {
    pub path: String,
    pub start: RustSourcePosition,
    pub end: RustSourcePosition,
}

/// One Cargo target identity owned by a workspace package.
#[derive(Clone, Debug, Deserialize, Eq, Ord, PartialEq, PartialOrd, Serialize)]
#[serde(deny_unknown_fields)]
pub struct RustTargetFact {
    pub identity: String,
    pub name: String,
    pub kinds: Vec<String>,
    pub source_root: String,
    pub entry_path: String,
    pub test: bool,
}

/// One declared Cargo dependency and its resolution evidence.
#[derive(Clone, Debug, Deserialize, Eq, Ord, PartialEq, PartialOrd, Serialize)]
#[serde(deny_unknown_fields)]
pub struct RustDependencyFact {
    pub package_name: String,
    pub source_name: String,
    pub kinds: Vec<String>,
    pub local_crate_identity: Option<String>,
    pub resolved: bool,
}

/// One Cargo workspace package with stable target and dependency identities.
#[derive(Clone, Debug, Deserialize, Eq, Ord, PartialEq, PartialOrd, Serialize)]
#[serde(deny_unknown_fields)]
pub struct RustCrateFact {
    pub identity: String,
    pub name: String,
    pub directory: String,
    pub manifest_path: String,
    pub library_name: Option<String>,
    pub targets: Vec<RustTargetFact>,
    pub dependencies: Vec<RustDependencyFact>,
}

/// One Fensu-owned Rust declaration independent of the parser implementation.
#[derive(Clone, Debug, Deserialize, Eq, Ord, PartialEq, PartialOrd, Serialize)]
#[serde(deny_unknown_fields)]
pub struct RustItemFact {
    pub kind: String,
    pub name: Option<String>,
    pub module_parts: Vec<String>,
    pub visibility: String,
    pub derives: Vec<String>,
    pub implemented_trait: Option<String>,
    pub implementation_target: Option<String>,
    pub location: RustSourceRange,
}

/// One authored `use` path and its strongest provable workspace resolution.
#[derive(Clone, Debug, Deserialize, Eq, Ord, PartialEq, PartialOrd, Serialize)]
#[serde(deny_unknown_fields)]
pub struct RustUseFact {
    pub source_path: String,
    pub source_module_parts: Vec<String>,
    pub authored_parts: Vec<String>,
    pub target_module_parts: Option<Vec<String>>,
    pub target_path: Option<String>,
    pub target_crate_identity: Option<String>,
    pub resolution: String,
    pub location: RustSourceRange,
}

/// Immutable facts collected for one Rust source file.
#[derive(Clone, Debug, Deserialize, Eq, Ord, PartialEq, PartialOrd, Serialize)]
#[serde(deny_unknown_fields)]
pub struct RustFileFact {
    pub path: String,
    pub crate_identity: String,
    pub crate_name: String,
    pub module_parts: Vec<String>,
    pub source_root: String,
    pub test: bool,
    pub source: String,
    pub parse_error: Option<String>,
    pub items: Vec<RustItemFact>,
    pub uses: Vec<RustUseFact>,
}

/// Complete versioned Rust facts transferred to the Python custom-rule host.
#[derive(Clone, Debug, Deserialize, Eq, PartialEq, Serialize)]
#[serde(deny_unknown_fields)]
pub struct RustWorkspaceFacts {
    pub schema_version: String,
    pub parser_contract: String,
    pub crates: Vec<RustCrateFact>,
    pub files: Vec<RustFileFact>,
}
