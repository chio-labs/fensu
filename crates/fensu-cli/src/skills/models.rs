use std::fmt;
use std::path::PathBuf;

use serde::{Deserialize, Serialize};

use crate::models::{Config, RuleMetadata};

#[derive(Clone, Copy, Debug, Eq, Hash, PartialEq)]
pub(crate) enum SkillTarget {
    Opencode,
    Claude,
    Agents,
}

impl SkillTarget {
    pub(crate) fn parse(value: &str) -> Option<Self> {
        match value {
            "opencode" => Some(Self::Opencode),
            "claude" => Some(Self::Claude),
            "agents" => Some(Self::Agents),
            _ => None,
        }
    }
}

#[derive(Clone, Debug, Default)]
pub(crate) struct SkillOptions {
    pub(crate) global_install: bool,
    pub(crate) targets: Vec<SkillTarget>,
    pub(crate) force: bool,
    pub(crate) check: bool,
    pub(crate) install_root: Option<String>,
    pub(crate) help: bool,
}

#[derive(Clone, Debug)]
pub(crate) struct SkillContext {
    pub(crate) config_path: PathBuf,
    pub(crate) project_root: PathBuf,
    pub(crate) install_root: PathBuf,
    pub(crate) git_root: Option<PathBuf>,
    pub(crate) project_prefix: String,
    pub(crate) identity: String,
    pub(crate) catalogue: Vec<RuleMetadata>,
    pub(crate) blocking: Vec<RuleMetadata>,
    pub(crate) warnings: Vec<RuleMetadata>,
    pub(crate) ignored: Vec<RuleMetadata>,
    pub(crate) config: Config,
}

#[derive(Clone, Debug)]
pub(crate) struct RuleSelection {
    pub(crate) catalogue: Vec<RuleMetadata>,
    pub(crate) blocking: Vec<RuleMetadata>,
    pub(crate) warnings: Vec<RuleMetadata>,
    pub(crate) ignored: Vec<RuleMetadata>,
}

#[derive(Clone, Debug)]
pub(crate) struct ProjectSkillFile {
    pub(crate) relative_path: PathBuf,
    pub(crate) content: Vec<u8>,
    pub(crate) mode: u32,
}

#[derive(Clone, Debug)]
pub(crate) struct ProjectSkillBundle {
    pub(crate) identity: String,
    pub(crate) files: Vec<ProjectSkillFile>,
}

#[derive(Clone, Debug)]
pub(crate) struct InstallTarget {
    pub(crate) path: PathBuf,
}

#[derive(Clone, Debug)]
pub(crate) struct ProjectInstallTarget {
    pub(crate) path: PathBuf,
    pub(crate) bundle: ProjectSkillBundle,
}

#[derive(Clone, Debug)]
pub(crate) struct InstallPlan {
    pub(crate) context: SkillContext,
    pub(crate) targets: Vec<InstallTarget>,
    pub(crate) project_targets: Vec<ProjectInstallTarget>,
    pub(crate) legacy_paths: Vec<PathBuf>,
    pub(crate) owner: String,
    pub(crate) input_fingerprint: String,
    pub(crate) synchronize_project_skills: bool,
}

#[derive(Clone, Debug, Deserialize, Serialize)]
pub(crate) struct Ownership {
    pub(crate) schema: u32,
    pub(crate) identity: String,
    pub(crate) owner: String,
    pub(crate) input_fingerprint: String,
    pub(crate) content_fingerprint: String,
}

#[derive(Clone, Copy, Debug, Eq, Ord, PartialEq, PartialOrd)]
pub(crate) enum FreshnessReason {
    Stale,
    Missing,
    Divergent,
    MalformedMarker,
    Collision,
}

impl fmt::Display for FreshnessReason {
    fn fmt(&self, formatter: &mut fmt::Formatter<'_>) -> fmt::Result {
        formatter.write_str(match self {
            Self::Stale => "stale",
            Self::Missing => "missing",
            Self::Divergent => "divergent",
            Self::MalformedMarker => "malformed-marker",
            Self::Collision => "collision",
        })
    }
}

#[derive(Clone, Debug)]
pub(crate) struct FreshnessIssue {
    pub(crate) path: PathBuf,
    pub(crate) reason: FreshnessReason,
}

#[derive(Clone, Debug)]
pub(crate) struct FreshnessResult {
    pub(crate) inspected_paths: Vec<PathBuf>,
    pub(crate) issues: Vec<FreshnessIssue>,
}

#[derive(Debug, Deserialize)]
pub(crate) struct HostResponse {
    pub(crate) protocol: u32,
    pub(crate) package_version: String,
    pub(crate) catalogue: Vec<RuleMetadata>,
    pub(crate) blocking: Vec<String>,
    pub(crate) warnings: Vec<String>,
    pub(crate) ignored: Vec<String>,
}
