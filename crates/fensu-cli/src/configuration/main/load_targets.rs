//! Load every selected analyzer target in deterministic name order.

use std::path::{Path, PathBuf};

use crate::configuration::_helpers::loading;
use crate::models::Config;

pub(crate) fn load_targets(
    start: &Path,
    target: Option<&str>,
) -> Result<Vec<(PathBuf, Config)>, String> {
    loading::load_targets(start, target)
}
