//! Snapshot rows describing walked repository files.

use std::ffi::OsString;
use std::path::PathBuf;

/// One walked Python entry with its canonical filesystem identity.
#[derive(Debug)]
pub struct WalkedEntry {
    pub entry_path: PathBuf,
    pub canonical_path: Option<PathBuf>,
    pub root_relative_parts: Option<Vec<OsString>>,
}

/// One supported repository metadata question.
#[derive(Clone, Copy, Debug)]
pub enum RepositoryStatKind {
    Exists,
    IsFile,
    IsDir,
}

/// One repository-relative metadata question.
#[derive(Debug)]
pub struct RepositoryStatQuery {
    pub relative_path: PathBuf,
    pub kind: RepositoryStatKind,
}

/// One resolved repository-relative identity and metadata answer.
#[derive(Debug, PartialEq, Eq)]
pub struct RepositoryStatAnswer {
    pub dependency_path: String,
    pub answer: bool,
}

/// One repository-relative Python glob question.
#[derive(Debug)]
pub struct RepositoryPythonGlobQuery {
    pub relative_path: PathBuf,
    pub recursive: bool,
}

/// One resolved repository-relative identity and ordered Python glob answer.
#[derive(Debug, PartialEq, Eq)]
pub struct RepositoryPythonGlobAnswer {
    pub dependency_path: String,
    pub answer: Vec<String>,
}

/// One supported repository source or namespace question.
#[derive(Clone, Copy, Debug)]
pub enum RepositoryContextKind {
    Source,
    DirectoryEntries,
    PythonAnchor,
}

/// One repository-relative source or namespace question.
#[derive(Debug)]
pub struct RepositoryContextQuery {
    pub relative_path: PathBuf,
    pub kind: RepositoryContextKind,
}

/// One resolved identity and source or namespace answer.
#[derive(Debug, PartialEq, Eq)]
pub struct RepositoryContextAnswer {
    pub dependency_path: String,
    pub source_answer: Option<String>,
    pub path_answer: Vec<String>,
}
