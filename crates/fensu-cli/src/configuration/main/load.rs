use std::path::{Path, PathBuf};

use crate::configuration::helpers::loading;
use crate::models::Config;

pub(crate) fn load(start: &Path) -> Result<(PathBuf, Config), String> {
    loading::load(start)
}
