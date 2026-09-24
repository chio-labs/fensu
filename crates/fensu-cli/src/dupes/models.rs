//! Options, configuration, units, and report models for `fensu dupes`.

use std::collections::BTreeMap;
use std::path::PathBuf;

use serde::Serialize;

#[derive(Clone, Debug)]
pub(crate) struct DupesOptions {
    pub(crate) json: bool,
    pub(crate) top: usize,
    pub(crate) min_similarity: f64,
    pub(crate) min_tokens: usize,
    pub(crate) languages: Vec<&'static str>,
    pub(crate) path_globs: Vec<String>,
    pub(crate) include_tests: bool,
    pub(crate) since: Option<String>,
    pub(crate) diff: bool,
}

#[derive(Clone, Debug, Default)]
pub(crate) struct DupesConfig {
    pub(crate) exclude: Vec<String>,
    pub(crate) allowlist: Vec<AllowlistEntry>,
    pub(crate) contract_exemptions: Vec<ContractExemption>,
}

#[derive(Clone, Debug)]
pub(crate) struct AllowlistEntry {
    pub(crate) paths: Vec<String>,
}

#[derive(Clone, Debug, Eq, Hash, Ord, PartialEq, PartialOrd)]
pub(crate) struct ClassKey {
    pub(crate) path: String,
    pub(crate) name: String,
}

#[derive(Clone, Debug)]
pub(crate) struct ContractExemption {
    pub(crate) contract: ClassKey,
    pub(crate) forbidden_owners: Vec<ClassKey>,
    pub(crate) paths: Vec<String>,
}

/// One analysable file resolved from the configured targets.
#[derive(Clone, Debug)]
pub(crate) struct DupesSource {
    pub(crate) path: PathBuf,
    pub(crate) repository_path: String,
    pub(crate) language: &'static str,
    pub(crate) content: Vec<u8>,
}

/// Discovered sources plus the repository facts analysis needs.
#[derive(Clone, Debug)]
pub(crate) struct DupesWorkspace {
    pub(crate) root: PathBuf,
    pub(crate) sources: Vec<DupesSource>,
    pub(crate) python_import_roots: Vec<String>,
    pub(crate) config: DupesConfig,
}

/// A function-level unit as produced by one language extractor.
#[derive(Clone, Debug, Default, Eq, PartialEq)]
pub(crate) struct ExtractedUnit {
    pub(crate) name: String,
    pub(crate) start_line: usize,
    pub(crate) end_line: usize,
    pub(crate) normalized: Vec<String>,
    pub(crate) concrete: Vec<String>,
}

/// Units from one Rust file plus the test-only module files it declares.
#[derive(Clone, Debug, Default)]
pub(crate) struct RustFileUnits {
    pub(crate) units: Vec<ExtractedUnit>,
    pub(crate) test_module_prefixes: Vec<String>,
}

#[derive(Clone, Debug)]
pub(crate) struct CloneUnit {
    pub(crate) language: &'static str,
    pub(crate) path: String,
    pub(crate) name: String,
    pub(crate) start_line: usize,
    pub(crate) end_line: usize,
    pub(crate) tokens: Vec<u32>,
    pub(crate) fingerprint_ids: Vec<u32>,
    pub(crate) concrete_key: u64,
}

#[derive(Clone, Copy, Debug, Eq, Ord, PartialEq, PartialOrd)]
pub(crate) enum Category {
    Exact,
    Renamed,
    NearMiss,
}

#[derive(Clone, Copy, Debug)]
pub(crate) struct ClonePair {
    pub(crate) left: usize,
    pub(crate) right: usize,
    pub(crate) similarity: f64,
    pub(crate) category: Category,
}

#[derive(Clone, Debug, Default)]
pub(crate) struct FileChanges {
    pub(crate) added_ranges: Vec<(usize, usize)>,
    pub(crate) deletion_points: Vec<usize>,
    pub(crate) whole_file: bool,
}

#[derive(Clone, Debug, Serialize)]
pub(crate) struct CloneMember {
    pub(crate) language: &'static str,
    pub(crate) path: String,
    pub(crate) name: String,
    pub(crate) start_line: usize,
    pub(crate) end_line: usize,
    pub(crate) tokens: usize,
    pub(crate) changed: bool,
    pub(crate) forced: bool,
}

#[derive(Clone, Debug, Serialize)]
pub(crate) struct ClusterLink {
    pub(crate) left: usize,
    pub(crate) right: usize,
    pub(crate) similarity: f64,
    pub(crate) category: &'static str,
}

#[derive(Clone, Debug, Serialize)]
pub(crate) struct DiffLine {
    pub(crate) member: usize,
    pub(crate) line: usize,
    pub(crate) text: String,
}

#[derive(Clone, Debug, Serialize)]
pub(crate) struct MemberDiff {
    pub(crate) left: usize,
    pub(crate) right: usize,
    pub(crate) identical: bool,
    pub(crate) lines: Vec<DiffLine>,
    pub(crate) omitted_lines: usize,
}

#[derive(Clone, Debug, Serialize)]
pub(crate) struct CloneCluster {
    pub(crate) category: &'static str,
    pub(crate) similarity_min: f64,
    pub(crate) similarity_max: f64,
    pub(crate) duplicated_tokens: usize,
    pub(crate) members: Vec<CloneMember>,
    pub(crate) links: Vec<ClusterLink>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub(crate) diff: Option<MemberDiff>,
}

#[derive(Clone, Debug)]
pub(crate) struct DupesReport {
    pub(crate) since: Option<String>,
    pub(crate) unit_counts: BTreeMap<&'static str, usize>,
    pub(crate) allowlisted_pairs: usize,
    pub(crate) contract_exempt_members: usize,
    pub(crate) clusters: Vec<CloneCluster>,
}
