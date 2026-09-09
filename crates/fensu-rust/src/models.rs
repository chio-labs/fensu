//! Parser-independent Rust analysis models owned by Fensu.

use std::path::PathBuf;

/// One parser-independent repository diagnostic.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct AnalysisDiagnostic {
    pub code: &'static str,
    pub path: PathBuf,
    pub line: Option<usize>,
    pub message: String,
    pub remediation: String,
}

/// Deterministically ordered analysis of one Cargo workspace.
#[derive(Clone, Debug, Default, Eq, PartialEq)]
pub struct RepositoryAnalysis {
    pub diagnostics: Vec<AnalysisDiagnostic>,
}
