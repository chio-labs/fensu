//! Load repository-rule routing policy.

use std::path::Path;

use crate::configuration::_helpers::loading;
use crate::models::RepositoryRulePolicy;

pub(crate) fn load_repository_rule_policy(
    start: &Path,
) -> Result<Option<RepositoryRulePolicy>, String> {
    loading::load_repository_rule_policy(start)
}
