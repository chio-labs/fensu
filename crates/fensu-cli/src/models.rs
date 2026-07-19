use std::collections::HashMap;
use std::path::PathBuf;

use fensu_facts::extension::models::ProgramHandle;
use serde::{Deserialize, Serialize};

#[derive(Debug)]
pub struct CliOutput {
    pub stdout: String,
    pub stderr: String,
    pub exit_code: i32,
}

impl CliOutput {
    pub fn success(stdout: String) -> Self {
        Self {
            stdout,
            stderr: String::new(),
            exit_code: 0,
        }
    }

    pub fn error(stderr: String) -> Self {
        Self {
            stdout: String::new(),
            stderr: format!("{stderr}\n"),
            exit_code: 2,
        }
    }

    pub fn delegated(exit_code: i32) -> Self {
        Self {
            stdout: String::new(),
            stderr: String::new(),
            exit_code,
        }
    }
}

#[derive(Debug, Default)]
pub(crate) struct InitOptions {
    pub(crate) yes: bool,
    pub(crate) roots: Vec<String>,
    pub(crate) tests: Vec<String>,
    pub(crate) tooling: Vec<String>,
    pub(crate) skills: Option<bool>,
    pub(crate) name: Option<String>,
    pub(crate) help: bool,
}

#[derive(Clone, Debug, Deserialize)]
pub(crate) struct RuleMetadata {
    pub(crate) code: String,
    pub(crate) family: String,
    pub(crate) slug: String,
    pub(crate) message: String,
    pub(crate) remediation: Option<String>,
    pub(crate) severity: String,
    pub(crate) enabled_by_default: bool,
    pub(crate) execution_owner: String,
}

#[derive(Clone, Debug, Default)]
pub(crate) struct Config {
    pub(crate) roots: Vec<String>,
    pub(crate) tests: Vec<String>,
    pub(crate) tooling: Vec<String>,
    pub(crate) select: Vec<String>,
    pub(crate) warn: Vec<String>,
    pub(crate) ignore: Vec<String>,
    pub(crate) rule_paths: Vec<String>,
    pub(crate) rule_modules: Vec<String>,
    pub(crate) cache_enabled: bool,
    pub(crate) evaluation_include: Vec<String>,
    pub(crate) evaluation_exclude: Vec<String>,
    pub(crate) thresholds: HashMap<String, u32>,
    pub(crate) role_thresholds: HashMap<String, HashMap<String, u32>>,
    pub(crate) threshold_overrides: Vec<ThresholdOverride>,
    pub(crate) contracts: Vec<(String, String)>,
    pub(crate) exceptions: Vec<RuleException>,
    pub(crate) memory_enabled: bool,
    pub(crate) raw: Vec<u8>,
}

#[derive(Clone, Debug, Default)]
pub(crate) struct ThresholdOverride {
    pub(crate) paths: Vec<String>,
    pub(crate) thresholds: HashMap<String, u32>,
    pub(crate) reason: String,
}

#[derive(Clone, Debug, Default)]
pub(crate) struct RuleException {
    pub(crate) rule: String,
    pub(crate) path: String,
    pub(crate) reason: String,
    pub(crate) symbols: Vec<String>,
}

#[derive(Clone, Debug)]
pub(crate) struct ScopedSource {
    pub(crate) path: PathBuf,
    pub(crate) repository_path: String,
    pub(crate) root: PathBuf,
    pub(crate) root_text: String,
    pub(crate) scope: String,
    pub(crate) relative_parts: Vec<String>,
    pub(crate) content: Vec<u8>,
    pub(crate) fingerprint: String,
    pub(crate) program: Option<ProgramHandle>,
}

#[derive(Clone, Debug, Serialize, Deserialize)]
pub(crate) struct Fault {
    pub(crate) code: String,
    pub(crate) path: String,
    pub(crate) line: Option<u32>,
    pub(crate) column: Option<u32>,
    pub(crate) message: String,
    pub(crate) remediation: Option<String>,
    pub(crate) warning: bool,
}

#[derive(Clone, Debug, Serialize, Deserialize)]
pub(crate) struct CachedOutput {
    pub(crate) identity: String,
    pub(crate) output: String,
    pub(crate) exit_code: i32,
    pub(crate) file_count: usize,
}

#[derive(Clone, Debug)]
pub(crate) struct CheckOptions {
    pub(crate) no_color: bool,
    pub(crate) warn: bool,
    pub(crate) cache_enabled: Option<bool>,
    pub(crate) cache_stats: bool,
    pub(crate) paths: Vec<String>,
}

#[derive(Clone, Debug, Eq, Ord, PartialEq, PartialOrd, Serialize, Deserialize)]
pub(crate) struct ThresholdUse {
    pub(crate) repository_path: String,
    pub(crate) threshold: String,
    pub(crate) override_order: usize,
    pub(crate) matched_pattern: String,
    pub(crate) reason: String,
    pub(crate) effective_value: u32,
}
