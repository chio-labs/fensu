//! Data models for the structure checker.

use std::path;

/// One structure violation with its actionable remediation.
#[derive(Debug, Clone)]
pub struct Violation {
    pub code: &'static str,
    pub path: path::PathBuf,
    pub line: Option<usize>,
    pub message: String,
    pub remediation: &'static str,
}

impl Violation {
    /// Build one violation record for a checked file.
    pub fn new(
        code: &'static str,
        path: &path::Path,
        line: Option<usize>,
        message: impl Into<String>,
        remediation: &'static str,
    ) -> Self {
        Self {
            code,
            path: path.to_path_buf(),
            line,
            message: message.into(),
            remediation,
        }
    }

    /// Deterministic ordering key: path, then line, then code.
    pub fn sort_key(&self) -> (String, usize, &'static str) {
        (
            self.path.to_string_lossy().into_owned(),
            self.line.unwrap_or(0),
            self.code,
        )
    }
}

/// One repository source file with its repo-relative location and content.
#[derive(Debug, Clone)]
pub struct SourceFile {
    pub path: path::PathBuf,
    pub relative: String,
    pub source: String,
}

/// Files and setup violations produced while scanning one source root.
#[derive(Debug)]
pub struct SourceScan {
    pub files: Vec<SourceFile>,
    pub violations: Vec<Violation>,
}

/// Workspace members and setup violations produced from the root manifest.
#[derive(Debug)]
pub struct WorkspaceScan {
    pub crate_directories: Vec<path::PathBuf>,
    pub violations: Vec<Violation>,
}

impl SourceFile {
    /// Return the file name portion of the path.
    pub fn file_name(&self) -> &str {
        self.relative.rsplit('/').next().unwrap_or_default()
    }

    /// Return the file stem without the .rs suffix.
    pub fn file_stem(&self) -> &str {
        self.file_name().trim_end_matches(".rs")
    }

    /// Return whether any directory component equals the given name.
    pub fn has_directory(&self, name: &str) -> bool {
        let components: Vec<&str> = self.relative.split('/').collect();
        components
            .iter()
            .take(components.len().saturating_sub(1))
            .any(|component| *component == name)
    }

    /// Return the number of source lines.
    pub fn line_count(&self) -> usize {
        self.source.lines().count()
    }

    /// Return the repository-relative path used in diagnostics.
    pub fn relative_path(&self) -> &path::Path {
        path::Path::new(&self.relative)
    }
}
