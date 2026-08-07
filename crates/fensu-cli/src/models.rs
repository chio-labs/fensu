use std::collections::HashMap;
use std::path::PathBuf;

use fensu_facts::extension::models::ProgramHandle;
use serde::{Deserialize, Serialize};

#[derive(Debug)]
pub(crate) struct CliOutput {
    pub(crate) stdout: String,
    pub(crate) stderr: String,
    pub(crate) exit_code: i32,
}

impl CliOutput {
    pub(crate) fn success(stdout: String) -> Self {
        Self {
            stdout,
            stderr: String::new(),
            exit_code: 0,
        }
    }

    pub(crate) fn error(stderr: String) -> Self {
        Self {
            stdout: String::new(),
            stderr: format!("{stderr}\n"),
            exit_code: 2,
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

#[derive(Clone, Debug, Default)]
pub(crate) struct Config {
    pub(crate) roots: Vec<String>,
    pub(crate) tests: Vec<String>,
    pub(crate) test_scopes: Vec<String>,
    pub(crate) tooling: Vec<String>,
    pub(crate) select: Vec<String>,
    pub(crate) warn: Vec<String>,
    pub(crate) ignore: Vec<String>,
    pub(crate) rule_paths: Vec<String>,
    pub(crate) rule_modules: Vec<String>,
    pub(crate) rule_packs: Vec<String>,
    pub(crate) rule_options: toml::map::Map<String, toml::Value>,
    pub(crate) cache_enabled: bool,
    pub(crate) cache_require_cacheable: bool,
    pub(crate) evaluation_include: Vec<String>,
    pub(crate) evaluation_exclude: Vec<String>,
    pub(crate) thresholds: HashMap<String, u32>,
    pub(crate) role_thresholds: HashMap<String, HashMap<String, u32>>,
    pub(crate) threshold_overrides: Vec<ThresholdOverride>,
    pub(crate) contracts: Vec<(String, String)>,
    pub(crate) exceptions: Vec<RuleException>,
    pub(crate) rule_ignores: Vec<RuleIgnore>,
    pub(crate) memory_enabled: bool,
    pub(crate) memory_archive_after_days: u64,
    pub(crate) skills_name: Option<String>,
    pub(crate) source_kind: String,
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

#[derive(Clone, Debug, Default)]
pub(crate) struct RuleIgnore {
    pub(crate) rules: Vec<String>,
    pub(crate) paths: Vec<String>,
    pub(crate) reason: String,
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
    pub(crate) alias_of: Option<String>,
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
    pub(crate) color: String,
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
