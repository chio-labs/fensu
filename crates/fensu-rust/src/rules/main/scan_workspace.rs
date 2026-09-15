//! Internal entry point for one authoritative Cargo workspace scan.

use std::path::Path;

use crate::models::WorkspaceScan;

pub(crate) fn scan_workspace(repository_root: &Path) -> WorkspaceScan {
    crate::rules::_helpers::sources::scanning::scan_workspace(repository_root)
}
