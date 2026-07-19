//! Snapshot rows describing walked repository files.

use std::collections::{HashMap, HashSet};
use std::ffi::OsString;
use std::path::PathBuf;

/// One walked Python entry with its canonical filesystem identity.
#[derive(Debug)]
pub struct WalkedEntry {
    pub entry_path: PathBuf,
    pub canonical_path: Option<PathBuf>,
    pub root_relative_parts: Option<Vec<OsString>>,
}

/// Filesystem metadata captured once for all dependency queries in a generation.
#[derive(Debug)]
pub struct RepositoryObservationIndex {
    pub(crate) repo_root: PathBuf,
    pub(crate) entries: Vec<String>,
    pub(crate) directory_order: Vec<String>,
    pub(crate) direct_entries: HashMap<String, Vec<String>>,
    pub(crate) file_paths: HashSet<String>,
    pub(crate) directory_paths: HashSet<String>,
}

/// One persisted repository query consumed by the shared observation index.
#[derive(Clone, Debug, PartialEq, Eq, Hash)]
pub struct RepositoryObservationQuery {
    pub relative_path: String,
    pub kind: String,
    pub pattern: Option<String>,
    pub recursive: bool,
}

/// One resolved repository query state produced from a shared traversal.
#[derive(Clone, Debug, PartialEq, Eq)]
pub struct RepositoryObservationState {
    pub dependency_path: String,
    pub answer: RepositoryObservationAnswer,
}

/// Supported canonical answers for persisted repository queries.
#[derive(Clone, Debug, PartialEq, Eq)]
pub enum RepositoryObservationAnswer {
    None,
    Bool(bool),
    String(String),
    Paths(Vec<String>),
}

impl RepositoryObservationAnswer {
    /// Return an ordered path answer when this query produces paths.
    pub fn as_paths(&self) -> Option<&[String]> {
        match self {
            Self::Paths(paths) => Some(paths),
            _ => None,
        }
    }
}

impl RepositoryObservationQuery {
    /// Observe this query through an already-built repository index.
    pub fn observe(
        &self,
        index: &RepositoryObservationIndex,
    ) -> Option<RepositoryObservationState> {
        index.observe(self)
    }
}
