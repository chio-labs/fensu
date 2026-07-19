//! Match and relativize walked filesystem names.

use std::ffi::{OsStr, OsString};
use std::path::Path;

use crate::constants::PYTHON_FILE_SUFFIX_BYTES;

pub(crate) fn has_python_suffix(name: &OsStr) -> bool {
    name.as_encoded_bytes().ends_with(PYTHON_FILE_SUFFIX_BYTES)
}

pub(crate) fn root_relative_parts(canonical: &Path, root: &Path) -> Option<Vec<OsString>> {
    let relative = canonical.strip_prefix(root).ok()?;
    Some(
        relative
            .components()
            .map(|component| component.as_os_str().to_owned())
            .collect(),
    )
}
