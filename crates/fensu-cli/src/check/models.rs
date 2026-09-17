//! Prepared check state and cache cleanup plans.

use std::path::Path;
use std::path::PathBuf;

use cap_std::fs::Dir;
use fensu_policy::lifecycle::models::Finding;
use fensu_rust::RustWorkspaceFacts;
use serde::{Deserialize, Serialize};

use crate::analyzer::AnalyzerId;
use crate::models::{Config, Fault, ProjectInput, ScopedSource, ThresholdUse};

#[derive(Debug)]
pub(crate) struct CheckIdentityRequest<'a> {
    pub(crate) root: &'a Path,
    pub(crate) project_root: &'a Path,
    pub(crate) config: &'a Config,
    pub(crate) sources: &'a [ScopedSource],
    pub(crate) project_inputs: &'a [ProjectInput],
    pub(crate) warnings: bool,
}

#[derive(Debug)]
pub(crate) struct CheckPlan {
    pub(crate) root: PathBuf,
    pub(crate) project_root: PathBuf,
    pub(crate) config: Config,
    pub(crate) sources: Vec<ScopedSource>,
    pub(crate) project_inputs: Vec<ProjectInput>,
    pub(crate) excluded: usize,
    pub(crate) identity: String,
    pub(crate) cache_enabled: bool,
    pub(crate) color: bool,
    pub(crate) repository_facts: Option<serde_json::Value>,
}

#[derive(Debug)]
pub(crate) struct CheckPlans {
    pub(crate) invocation: PathBuf,
    pub(crate) config_target: Option<String>,
    pub(crate) check_skill_freshness: bool,
    pub(crate) root: PathBuf,
    pub(crate) plans: Vec<CheckPlan>,
    pub(crate) sources: Vec<ScopedSource>,
    pub(crate) identity: String,
    pub(crate) cache_enabled: bool,
    pub(crate) color: bool,
}

#[derive(Clone, Debug, Deserialize, Serialize)]
pub(crate) struct CheckResult {
    pub(crate) analyzer: AnalyzerId,
    pub(crate) faults: Vec<Fault>,
    pub(crate) warnings: Vec<Fault>,
    pub(crate) selected: usize,
    pub(crate) excluded: usize,
    pub(crate) applied_exceptions: usize,
    pub(crate) threshold_uses: Vec<ThresholdUse>,
    #[serde(default)]
    pub(crate) cacheable: Option<bool>,
}

#[derive(Clone, Debug, Default, Deserialize, Serialize)]
pub(crate) struct CheckCacheStats {
    pub(crate) hits: usize,
    pub(crate) misses: usize,
    pub(crate) invalidations: usize,
    pub(crate) writes: usize,
    pub(crate) non_cacheable: usize,
}

impl CheckCacheStats {
    pub(crate) fn merge(&mut self, other: &Self) {
        self.hits += other.hits;
        self.misses += other.misses;
        self.invalidations += other.invalidations;
        self.writes += other.writes;
        self.non_cacheable += other.non_cacheable;
    }
}

#[derive(Debug, Deserialize)]
pub(crate) struct HostedCheckResponse {
    pub(crate) protocol: u32,
    pub(crate) package_version: String,
    pub(crate) error: Option<String>,
    pub(crate) results: Vec<CheckResult>,
    pub(crate) cache: Option<CheckCacheStats>,
    pub(crate) messages: Vec<String>,
    pub(crate) show_cache_stats: bool,
}

#[derive(Debug)]
pub(crate) struct StructuredCheckExecution {
    pub(crate) results: Vec<CheckResult>,
    pub(crate) cache: Option<CheckCacheStats>,
    pub(crate) messages: Vec<String>,
    pub(crate) root: PathBuf,
    pub(crate) color: bool,
    pub(crate) show_warnings: bool,
    pub(crate) repository_targets: Vec<RepositoryTargetPayload>,
}

#[derive(Clone, Copy, Debug)]
pub(crate) struct CheckOutputOptions {
    pub(crate) color: bool,
    pub(crate) show_warnings: bool,
    pub(crate) show_cache_stats: bool,
}

#[derive(Debug, Deserialize, Serialize)]
pub(crate) struct StructuredCachePayload {
    pub(crate) results: Vec<CheckResult>,
    #[serde(default)]
    pub(crate) repository_targets: Vec<RepositoryTargetPayload>,
}

#[derive(Debug)]
pub(crate) struct CleanupPlan {
    pub(crate) repository: Dir,
    pub(crate) configs: Vec<Config>,
}

#[derive(Clone, Copy, Debug)]
pub(crate) struct CheckRouting<'a> {
    pub(crate) help: bool,
    pub(crate) target: Option<&'a str>,
}

#[derive(Debug)]
pub(crate) struct EvaluationRequest<'a> {
    pub(crate) project_root: &'a Path,
    pub(crate) config: &'a Config,
    pub(crate) sources: &'a [ScopedSource],
    pub(crate) project_inputs: &'a [ProjectInput],
    pub(crate) excluded: usize,
    pub(crate) show_warnings: bool,
    pub(crate) cache_enabled: bool,
    pub(crate) collect_repository_facts: bool,
}

#[derive(Debug)]
pub(crate) struct TargetEvaluation {
    pub(crate) result: CheckResult,
    pub(crate) repository_facts: Option<serde_json::Value>,
}

#[derive(Clone, Debug, Deserialize, Serialize)]
pub(crate) struct CustomRuleSubject {
    pub(crate) path: String,
    pub(crate) scope: String,
    pub(crate) scope_root: String,
    pub(crate) relative_parts: Vec<String>,
}

#[derive(Clone, Debug, Deserialize, Serialize)]
#[serde(deny_unknown_fields)]
pub(crate) struct RepositoryTargetPayload {
    pub(crate) name: String,
    pub(crate) analyzer: AnalyzerId,
    pub(crate) root: String,
    pub(crate) ownership_depth: usize,
    pub(crate) facts: serde_json::Value,
    pub(crate) subjects: Vec<CustomRuleSubject>,
}

#[derive(Clone, Debug, Serialize)]
pub(crate) struct RepositoryCustomRulePayload {
    pub(crate) show_warnings: bool,
    pub(crate) cache_enabled: bool,
    pub(crate) targets: Vec<RepositoryTargetPayload>,
}

#[derive(Clone, Debug, Deserialize)]
#[serde(deny_unknown_fields)]
pub(crate) struct RepositoryCustomDependency {
    pub(crate) requester: String,
    pub(crate) target: String,
    pub(crate) kind: String,
    pub(crate) query: String,
    #[serde(rename = "answer")]
    pub(crate) _answer: String,
}

#[derive(Clone, Debug, Deserialize)]
#[serde(deny_unknown_fields)]
pub(crate) struct RepositoryCustomRuleResponse {
    pub(crate) findings: Vec<Finding>,
    pub(crate) blocking_codes: Vec<String>,
    pub(crate) warning_codes: Vec<String>,
    pub(crate) dependencies: Vec<RepositoryCustomDependency>,
    pub(crate) cacheable: bool,
    pub(crate) applied_exceptions: usize,
    pub(crate) cache: Option<CheckCacheStats>,
}

#[derive(Clone, Debug, Serialize)]
pub(crate) struct RustCustomRulePayload {
    pub(crate) target: Option<String>,
    pub(crate) show_warnings: bool,
    pub(crate) cache_enabled: bool,
    pub(crate) facts: RustWorkspaceFacts,
    pub(crate) subjects: Vec<CustomRuleSubject>,
}

#[derive(Clone, Debug, Deserialize)]
#[serde(deny_unknown_fields)]
pub(crate) struct RustCustomDependency {
    pub(crate) requester: String,
    pub(crate) kind: String,
    pub(crate) query: String,
    #[serde(rename = "answer")]
    pub(crate) _answer: String,
}

#[derive(Clone, Debug, Deserialize)]
#[serde(deny_unknown_fields)]
pub(crate) struct RustCustomRuleResponse {
    pub(crate) findings: Vec<Finding>,
    pub(crate) blocking_codes: Vec<String>,
    pub(crate) warning_codes: Vec<String>,
    pub(crate) dependencies: Vec<RustCustomDependency>,
    pub(crate) cacheable: bool,
}

#[derive(Clone, Debug, Serialize)]
pub(crate) struct WebCustomRulePayload {
    pub(crate) target: Option<String>,
    pub(crate) show_warnings: bool,
    pub(crate) cache_enabled: bool,
    pub(crate) facts: serde_json::Value,
    pub(crate) subjects: Vec<CustomRuleSubject>,
}

#[derive(Clone, Debug, Deserialize)]
#[serde(deny_unknown_fields)]
pub(crate) struct WebCustomRuleResponse {
    pub(crate) findings: Vec<Finding>,
    pub(crate) blocking_codes: Vec<String>,
    pub(crate) warning_codes: Vec<String>,
    pub(crate) dependencies: Vec<RustCustomDependency>,
    pub(crate) cacheable: bool,
}
