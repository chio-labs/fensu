//! Prepared check state and cache cleanup plans.

use std::path::Path;
use std::path::PathBuf;

use cap_std::fs::Dir;

use crate::models::{Config, ScopedSource};

#[derive(Debug)]
pub(crate) struct CheckIdentityRequest<'a> {
    pub(crate) root: &'a Path,
    pub(crate) project_root: &'a Path,
    pub(crate) config: &'a Config,
    pub(crate) sources: &'a [ScopedSource],
    pub(crate) warnings: bool,
}

#[derive(Debug)]
pub(crate) struct CheckPlan {
    pub(crate) invocation: PathBuf,
    pub(crate) root: PathBuf,
    pub(crate) project_root: PathBuf,
    pub(crate) config: Config,
    pub(crate) sources: Vec<ScopedSource>,
    pub(crate) excluded: usize,
    pub(crate) identity: String,
    pub(crate) cache_enabled: bool,
    pub(crate) color: bool,
}

#[derive(Debug)]
pub(crate) struct CleanupPlan {
    pub(crate) repository: Dir,
    pub(crate) config: Config,
}

#[derive(Clone, Copy, Debug)]
pub(crate) struct CheckRouting<'a> {
    pub(crate) help: bool,
    pub(crate) target: Option<&'a str>,
}

#[derive(Debug)]
pub(crate) struct EvaluationRequest<'a> {
    pub(crate) root: &'a Path,
    pub(crate) project_root: &'a Path,
    pub(crate) config: &'a Config,
    pub(crate) sources: &'a [ScopedSource],
    pub(crate) excluded: usize,
    pub(crate) show_warnings: bool,
    pub(crate) color: bool,
}
