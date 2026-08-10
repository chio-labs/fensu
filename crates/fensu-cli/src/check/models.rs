//! Prepared check state and cache cleanup plans.

use std::path::Path;
use std::path::PathBuf;

use cap_std::fs::Dir;

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

#[derive(Debug)]
pub(crate) struct CheckResult {
    pub(crate) analyzer: AnalyzerId,
    pub(crate) faults: Vec<Fault>,
    pub(crate) warnings: Vec<Fault>,
    pub(crate) selected: usize,
    pub(crate) excluded: usize,
    pub(crate) applied_exceptions: usize,
    pub(crate) threshold_uses: Vec<ThresholdUse>,
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
}
