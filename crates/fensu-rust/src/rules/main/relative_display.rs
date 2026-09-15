//! Internal entry point for portable repository-relative Rust paths.

use std::path::Path;

pub(crate) fn relative_display(repository_root: &Path, path: &Path) -> String {
    crate::rules::_helpers::sources::scanning::relative_display(repository_root, path)
}
