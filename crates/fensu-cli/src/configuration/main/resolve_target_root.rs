//! Resolve one validated target root from its repository boundary.

use std::path::{Path, PathBuf};

pub(crate) fn resolve_target_root(
    repository_root: &Path,
    configured: &str,
) -> Result<PathBuf, String> {
    crate::configuration::_helpers::roots::resolve_target_root(repository_root, configured)
}
