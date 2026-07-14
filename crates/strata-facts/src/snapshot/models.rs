//! Snapshot rows describing walked repository files.

use std::ffi::OsString;
use std::path::PathBuf;

/// One walked Python entry with its canonical filesystem identity.
#[derive(Debug)]
pub struct WalkedEntry {
    pub entry_path: PathBuf,
    pub canonical_path: Option<PathBuf>,
    pub root_relative_parts: Option<Vec<OsString>>,
}
