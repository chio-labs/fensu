//! Read one repository-level configuration section without target validation.

use std::path::{Path, PathBuf};

use crate::configuration::_helpers::loading;

pub(crate) fn load_config_section(
    start: &Path,
    key: &str,
) -> Result<(PathBuf, Option<toml::Value>), String> {
    loading::load_section(start, key)
}
