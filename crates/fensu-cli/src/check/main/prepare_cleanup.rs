//! Capture the cache cleanup plan before a check runs.

use std::path::Path;

use crate::check::models::CleanupPlan;

pub(crate) fn prepare_cleanup(invocation: &Path, target: Option<&str>) -> Option<CleanupPlan> {
    crate::check::_helpers::cleanup::prepare(invocation, target)
}
