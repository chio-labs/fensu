//! Observe package entries and embedded targets before a cached result is read.

use std::path::Path;

/// Return deterministic observation fields for the discovered Cargo and Rust inputs.
pub fn file_placement_observations(root: &Path) -> Result<Vec<String>, String> {
    let root = root.canonicalize().map_err(|error| error.to_string())?;
    crate::rules::_helpers::repository::placement_observations::collect(&root)
}
