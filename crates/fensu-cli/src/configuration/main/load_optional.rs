use std::path::{Path, PathBuf};

use crate::configuration::helpers::loading;
use crate::models::Config;

pub(crate) fn load_optional(start: &Path) -> Result<Option<(PathBuf, Config)>, String> {
    loading::load_optional(start)
}
