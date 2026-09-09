//! Data models for the structure checker.

use std::collections::BTreeMap;
use std::path;

use serde::Deserialize;

use crate::configuration::main::validate_repository_policy::validate_repository_policy;
use crate::constants;

/// Versioned repository-specific identities layered over shared structure policy.
#[derive(Debug, Clone, Deserialize, Eq, PartialEq)]
#[serde(rename_all = "kebab-case", deny_unknown_fields)]
pub struct CheckerConfig {
    pub schema_version: u32,
    pub tooling: ToolingConfig,
    pub raw_parser_boundary: RawParserBoundaryConfig,
    #[serde(default)]
    pub repository: RepositoryPolicyConfig,
}

/// Identity and dependency boundaries for the repository's checker adapter.
#[derive(Debug, Clone, Deserialize, Eq, PartialEq)]
#[serde(rename_all = "kebab-case", deny_unknown_fields)]
pub struct ToolingConfig {
    pub package: String,
    pub runtime_forbidden_packages: Vec<String>,
    #[serde(default)]
    pub runtime_allowed_packages: Vec<String>,
}

/// Parser packages hidden behind the repository's shared fact model.
#[derive(Debug, Clone, Deserialize, Eq, PartialEq)]
#[serde(rename_all = "kebab-case", deny_unknown_fields)]
pub struct RawParserBoundaryConfig {
    pub packages: Vec<String>,
    pub remediation: String,
    #[serde(
        default = "crate::configuration::_helpers::repository_policy::default_raw_parser_restricted_paths"
    )]
    pub restricted_paths: Vec<String>,
}

/// Reviewed repository identities, structural paths, and adjustable budgets.
#[derive(Debug, Clone, Default, Deserialize, Eq, PartialEq)]
#[serde(rename_all = "kebab-case", deny_unknown_fields)]
pub struct RepositoryPolicyConfig {
    #[serde(default)]
    pub crate_names: Vec<String>,
    #[serde(default)]
    pub domain_paths: Vec<String>,
    #[serde(default)]
    pub role_paths: Vec<String>,
    #[serde(default)]
    pub intentional_layout_paths: Vec<String>,
    #[serde(default)]
    pub thresholds: ThresholdConfig,
}

/// Small consumer-adjustable subset of the shared structure budgets.
#[derive(Debug, Clone, Deserialize, Eq, PartialEq)]
#[serde(default, rename_all = "kebab-case", deny_unknown_fields)]
pub struct ThresholdConfig {
    pub max_file_lines: usize,
    pub max_arguments: usize,
    pub max_statements_global: usize,
    pub max_statements_entry: usize,
    pub max_distinct_calls_entry: usize,
    pub max_locals_entry: usize,
    pub max_helper_container_modules: usize,
    pub max_main_container_modules: usize,
}

impl Default for ThresholdConfig {
    fn default() -> Self {
        Self {
            max_file_lines: constants::MAX_FILE_LINES,
            max_arguments: constants::MAX_ARGUMENTS,
            max_statements_global: constants::MAX_STATEMENTS_GLOBAL,
            max_statements_entry: constants::MAX_STATEMENTS_ENTRY,
            max_distinct_calls_entry: constants::MAX_DISTINCT_CALLS_ENTRY,
            max_locals_entry: constants::MAX_LOCALS_ENTRY,
            max_helper_container_modules: constants::MAX_HELPER_CONTAINER_MODULES,
            max_main_container_modules: constants::MAX_MAIN_CONTAINER_MODULES,
        }
    }
}

impl Default for CheckerConfig {
    fn default() -> Self {
        Self {
            schema_version: constants::CHECKER_CONFIG_SCHEMA_VERSION,
            tooling: ToolingConfig {
                package: constants::DEFAULT_TOOLING_CRATE_NAME.to_owned(),
                runtime_forbidden_packages: vec![constants::DEFAULT_TOOLING_CRATE_NAME.to_owned()],
                runtime_allowed_packages: vec![constants::DEFAULT_ENGINE_CRATE_NAME.to_owned()],
            },
            raw_parser_boundary: RawParserBoundaryConfig {
                packages: constants::DEFAULT_RAW_PARSER_CRATES
                    .iter()
                    .map(|value| (*value).to_owned())
                    .collect(),
                remediation: constants::DEFAULT_RAW_PARSER_REMEDIATION.to_owned(),
                restricted_paths: crate::configuration::_helpers::repository_policy::default_raw_parser_restricted_paths(),
            },
            repository: RepositoryPolicyConfig::default(),
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
        crate::configuration::_helpers::repository_policy::validate_non_empty_unique(
            &self.tooling.runtime_allowed_packages,
            "runtime allowed packages",
        )?;
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
        crate::configuration::_helpers::repository_policy::validate_non_empty_unique(
            &self.raw_parser_boundary.restricted_paths,
            "raw parser restricted paths",
        )?;
        if let Some(path) = self
            .raw_parser_boundary
            .restricted_paths
            .iter()
            .find(|path| {
                !crate::configuration::_helpers::repository_policy::valid_repository_path(path)
            })
        {
            return Err(format!(
                "structure-checker raw parser restricted paths must be repository-relative POSIX paths: {path}"
            ));
        }
        validate_repository_policy(&self.repository)
    }

    /// Return whether aggregate layout rules intentionally exclude this exact subtree.
    pub(crate) fn is_intentional_layout(&self, relative: &str) -> bool {
        self.repository
            .intentional_layout_paths
            .iter()
            .any(|root| relative == root || relative.starts_with(&format!("{root}/")))
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
    pub source_root_relative: String,
    pub source_relative: String,
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

/// One Cargo workspace package and its resolved targets and dependencies.
#[derive(Debug, Clone)]
pub struct WorkspaceCrate {
    pub directory: path::PathBuf,
    pub package_name: Option<String>,
    pub package_identity: String,
    pub library_name: Option<String>,
    pub targets: Vec<WorkspaceTarget>,
    pub dependencies: Vec<WorkspaceDependency>,
}

/// One Cargo target source root and whether it follows test conventions.
#[derive(Debug, Clone, Eq, PartialEq)]
pub struct WorkspaceTarget {
    pub source_root: path::PathBuf,
    pub test: bool,
}

/// One Cargo-resolved dependency identity and optional local source path.
#[derive(Debug, Clone, Eq, PartialEq)]
pub struct WorkspaceDependency {
    pub package_name: String,
    pub source_name: String,
    pub path: Option<path::PathBuf>,
    pub resolved: bool,
}

/// Inputs needed to check one library source file under consumer policy.
#[derive(Debug)]
pub(crate) struct SourceCheckRequest<'a> {
    pub repo_root: &'a path::Path,
    pub src_root: &'a path::Path,
    pub file: &'a SourceFile,
    pub config: &'a CheckerConfig,
    pub dependencies: &'a [WorkspaceDependency],
    pub is_tooling_crate: bool,
}

/// Inputs needed to check one integration-test source file.
#[derive(Debug)]
pub(crate) struct TestCheckRequest<'a> {
    pub repo_root: &'a path::Path,
    pub tests_root: &'a path::Path,
    pub file: &'a SourceFile,
    pub config: &'a CheckerConfig,
    pub dependencies: &'a [WorkspaceDependency],
}

/// Inputs needed to check function shape for one parsed source file.
#[derive(Debug)]
pub(crate) struct SourceShapeCheckRequest<'a> {
    pub(crate) file: &'a SourceFile,
    pub(crate) syntax: &'a syn::File,
    pub(crate) kind: crate::types::FileKind,
    pub(crate) is_tooling_crate: bool,
    pub(crate) thresholds: &'a ThresholdConfig,
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

impl WorkspaceCrate {
    pub(crate) fn source_name(&self) -> Option<String> {
        self.library_name.clone().or_else(|| {
            self.package_name
                .as_ref()
                .map(|name| name.replace('-', "_"))
        })
    }

    pub(crate) fn graph_identity(&self) -> String {
        self.package_identity.clone()
    }

    pub(crate) fn reference_roots(
        &self,
        workspace_crates: &[WorkspaceCrate],
    ) -> BTreeMap<String, String> {
        let mut roots: BTreeMap<String, String> = BTreeMap::new();
        if let Some(source_name) = self.source_name() {
            roots.insert(source_name, self.graph_identity());
        }
        for dependency in &self.dependencies {
            if !dependency.resolved {
                continue;
            }
            for workspace_crate in workspace_crates {
                if dependency.path.as_ref() != Some(&workspace_crate.directory) {
                    continue;
                }
                roots.insert(
                    dependency.source_name.clone(),
                    workspace_crate.graph_identity(),
                );
                break;
            }
        }
        roots
    }
}
