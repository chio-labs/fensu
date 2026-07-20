use std::path::PathBuf;

use crate::skills::helpers::installation::{freshness, plan, publication};
use crate::skills::models::{
    FreshnessResult, InstallPlan, ProjectSkillBundle, SkillContext, SkillOptions,
};

pub(crate) fn build_plan(
    context: &SkillContext,
    options: &SkillOptions,
    bundles: Option<&[ProjectSkillBundle]>,
) -> Result<InstallPlan, String> {
    plan::build(context, options, bundles)
}

pub(crate) fn check(plan: &InstallPlan, authoritative: bool) -> Result<FreshnessResult, String> {
    freshness::check(plan, authoritative)
}

pub(crate) fn install(
    plan: &InstallPlan,
    generated: &[u8],
    force: bool,
) -> Result<Vec<PathBuf>, String> {
    publication::install(plan, generated, force)
}
