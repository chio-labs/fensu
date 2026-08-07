use std::fs;
use std::path::{Path, PathBuf};

use crate::constants::{CONFIG_FENSU_FILE, CONFIG_PYPROJECT_FILE};

pub(crate) fn find(start: &Path) -> Result<(PathBuf, bool), String> {
    let resolved = start.canonicalize().map_err(|error| error.to_string())?;
    for directory in resolved.ancestors() {
        let fensu = directory.join(CONFIG_FENSU_FILE);
        if fensu.is_file() {
            return Ok((fensu, false));
        }
        let pyproject = directory.join(CONFIG_PYPROJECT_FILE);
        if pyproject.is_file() {
            let text = fs::read_to_string(&pyproject)
                .map_err(|error| format!("Cannot read {}: {error}", pyproject.display()))?;
            let document = toml::from_slice::<toml::Value>(text.as_bytes())
                .map_err(|error| format!("Could not parse {}: {error}", pyproject.display()))?;
            if document
                .get("tool")
                .and_then(|value| value.get("fensu"))
                .is_some_and(toml::Value::is_table)
            {
                return Ok((pyproject, true));
            }
        }
    }
    Err("Could not find fensu.toml or [tool.fensu] in pyproject.toml.".to_owned())
}
