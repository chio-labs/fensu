//! Remove Python cache directories the check run created.

use crate::check::models::CleanupPlan;

pub(crate) fn clean_caches(plan: &CleanupPlan) {
    crate::check::_helpers::cleanup::cleanup_configured_roots(&plan.repository, &plan.configs);
}
