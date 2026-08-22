//! Data models for the structure checker.

use std::path;

use serde::Deserialize;

use crate::constants;

/// Versioned repository-specific identities layered over shared structure policy.
#[derive(Debug, Clone, Deserialize, Eq, PartialEq)]
#[serde(rename_all = "kebab-case", deny_unknown_fields)]
pub struct CheckerConfig {
    pub schema_version: u32,
    pub tooling: ToolingConfig,
    pub raw_parser_boundary: RawParserBoundaryConfig,
}

/// Identity and dependency boundaries for the repository's checker adapter.
#[derive(Debug, Clone, Deserialize, Eq, PartialEq)]
#[serde(rename_all = "kebab-case", deny_unknown_fields)]
pub struct ToolingConfig {
    pub package: String,
    pub runtime_forbidden_packages: Vec<String>,
}

/// Parser packages hidden behind the repository's shared fact model.
#[derive(Debug, Clone, Deserialize, Eq, PartialEq)]
#[serde(rename_all = "kebab-case", deny_unknown_fields)]
pub struct RawParserBoundaryConfig {
    pub packages: Vec<String>,
    pub remediation: String,
}

impl Default for CheckerConfig {
    fn default() -> Self {
        Self {
            schema_version: constants::CHECKER_CONFIG_SCHEMA_VERSION,
            tooling: ToolingConfig {
                package: constants::DEFAULT_TOOLING_CRATE_NAME.to_owned(),
                runtime_forbidden_packages: vec![constants::DEFAULT_TOOLING_CRATE_NAME.to_owned()],
            },
            raw_parser_boundary: RawParserBoundaryConfig {
                packages: constants::DEFAULT_RAW_PARSER_CRATES
                    .iter()
                    .map(|value| (*value).to_owned())
                    .collect(),
                remediation: constants::DEFAULT_RAW_PARSER_REMEDIATION.to_owned(),
            },
        }
    }
}

impl CheckerConfig {
    /// Reject unsupported versions and identities that cannot match a package.
    pub fn validate(&self) -> Result<(), String> {
        if self.schema_version != constants::CHECKER_CONFIG_SCHEMA_VERSION {
            return Err(format!(
                "unsupported structure-checker config schema version {}; expected {}",
                self.schema_version,
                constants::CHECKER_CONFIG_SCHEMA_VERSION
            ));
        }
        if self.tooling.package.trim().is_empty() {
            return Err("structure-checker tooling package must not be empty".to_owned());
        }
        if self
            .tooling
            .runtime_forbidden_packages
            .iter()
            .any(|package| package.trim().is_empty())
        {
            return Err("forbidden tooling package names must not be empty".to_owned());
        }
        if self
            .raw_parser_boundary
            .packages
            .iter()
            .any(|package| package.trim().is_empty())
        {
            return Err("raw parser package names must not be empty".to_owned());
        }
        if !self.raw_parser_boundary.packages.is_empty()
            && self.raw_parser_boundary.remediation.trim().is_empty()
        {
            return Err("raw parser remediation must not be empty".to_owned());
        }
        Ok(())
    }
}

/// One structure violation with its actionable remediation.
#[derive(Debug, Clone, Eq, PartialEq)]
pub struct Violation {
    pub code: &'static str,
    pub path: path::PathBuf,
    pub line: Option<usize>,
    pub message: String,
    pub remediation: String,
}

/// Named inputs for one structure violation.
#[derive(Debug)]
pub struct ViolationRequest<'a, Message, Remediation = &'static str> {
    pub code: &'static str,
    pub path: &'a path::Path,
    pub line: Option<usize>,
    pub message: Message,
    pub remediation: Remediation,
}

impl Violation {
    /// Build one violation record for a checked file.
    pub fn new<Message, Remediation>(request: ViolationRequest<'_, Message, Remediation>) -> Self
    where
        Message: Into<String>,
        Remediation: Into<String>,
    {
        Self {
            code: request.code,
            path: request.path.to_path_buf(),
            line: request.line,
            message: request.message.into(),
            remediation: request.remediation.into(),
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
    pub crates: Vec<WorkspaceCrate>,
    pub violations: Vec<Violation>,
}

/// One explicit workspace member and its best-effort manifest identity.
#[derive(Debug, Clone)]
pub struct WorkspaceCrate {
    pub directory: path::PathBuf,
    pub package_name: Option<String>,
}

/// Inputs needed to check one library source file under consumer policy.
#[derive(Debug)]
pub(crate) struct SourceCheckRequest<'a> {
    pub repo_root: &'a path::Path,
    pub src_root: &'a path::Path,
    pub file: &'a SourceFile,
    pub config: &'a CheckerConfig,
    pub is_tooling_crate: bool,
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
