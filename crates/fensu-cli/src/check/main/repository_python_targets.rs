//! Build Python target facts for the aggregate repository-rule host.

use std::collections::HashSet;

use crate::check::models::RepositoryTargetPayload;

pub(crate) fn repository_python_targets(
    arguments: &[String],
    target_names: &HashSet<String>,
) -> Result<Vec<RepositoryTargetPayload>, String> {
    crate::check::_helpers::execution::repository_python_targets(arguments, target_names)
}
