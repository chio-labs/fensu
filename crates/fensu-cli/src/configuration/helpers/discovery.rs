use std::fs;
use std::path::{Path, PathBuf};

use crate::constants::{CONFIG_FENSU_FILE, CONFIG_PYPROJECT_FILE, CONFIG_PYPROJECT_HEADER};

pub(crate) fn find(start: &Path) -> Result<(PathBuf, bool), String> {
    let resolved = start.canonicalize().map_err(|error| error.to_string())?;
    for directory in resolved.ancestors() {
        let fensu = directory.join(CONFIG_FENSU_FILE);
        if fensu.is_file() {
            return Ok((fensu, false));
        }
        let pyproject = directory.join(CONFIG_PYPROJECT_FILE);
        if pyproject.is_file() {
            let text = fs::read_to_string(&pyproject).unwrap_or_default();
            if text.contains(CONFIG_PYPROJECT_HEADER) {
                return Ok((pyproject, true));
            }
        }
    }
    Err("Could not find fensu.toml or [tool.fensu] in pyproject.toml.".to_owned())
}
