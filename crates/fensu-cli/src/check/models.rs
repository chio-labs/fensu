//! Prepared check state and cache cleanup plans.

use std::path::PathBuf;

use cap_std::fs::Dir;

use crate::models::{Config, ScopedSource};

#[derive(Debug)]
pub(crate) struct CheckPlan {
    pub(crate) invocation: PathBuf,
    pub(crate) root: PathBuf,
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
