//! Load repository-rule configuration for catalogue and skills commands.

use std::path::{Path, PathBuf};

use crate::configuration::_helpers::loading;
use crate::models::Config;

pub(crate) fn load_repository_rule_config(
    start: &Path,
) -> Result<Option<(PathBuf, Config)>, String> {
    loading::load_repository_rule_config(start)
}
