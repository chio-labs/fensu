use std::path::{Path, PathBuf};

use crate::configuration::_helpers::loading;
use crate::models::Config;

pub(crate) fn load_target(start: &Path, target: Option<&str>) -> Result<(PathBuf, Config), String> {
    loading::load_target(start, target)
}
