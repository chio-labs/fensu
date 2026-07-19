//! Hash source file contents in parallel for snapshot fingerprints.

use std::path::{Path, PathBuf};

use rayon::iter::{IntoParallelRefIterator, ParallelIterator};
use sha2::{Digest, Sha256};

/// Return the lowercase hex SHA-256 of each readable file's raw bytes.
pub fn hash_files(paths: &[PathBuf]) -> Vec<Option<String>> {
    paths.par_iter().map(|path| hashed_file(path)).collect()
}

fn hashed_file(path: &Path) -> Option<String> {
    let bytes = std::fs::read(path).ok()?;
    Some(hex::encode(Sha256::digest(bytes)))
}
