//! Build one shared native repository observation index.

use std::path::Path;

use crate::snapshot::models::{RepositoryObservationIndex, RepositoryObservationQuery};

pub fn build_repository_observation_index(
    repo_root: &Path,
    queries: &[RepositoryObservationQuery],
) -> Option<RepositoryObservationIndex> {
    RepositoryObservationIndex::build(repo_root, queries)
}
