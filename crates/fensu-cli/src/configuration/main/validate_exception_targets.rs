use std::path::Path;

use crate::configuration::helpers::exception_targets;
use crate::models::Config;

pub(crate) fn validate_exception_targets(
    config: &Config,
    project_root: &Path,
) -> Result<(), String> {
    exception_targets::validate_targets(config, project_root)
}
