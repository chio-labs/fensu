//! Archive canonical memory sources and synchronize the generated index.

use crate::engine::_helpers::archival::archive;
use crate::engine::errors::MemoryIndexError;
use crate::engine::models::{MemoryArchiveRequest, MemoryArchiveResult};

/// Plan, publish, and synchronize one explicit or age-based archive operation.
pub fn archive_memory(
    request: MemoryArchiveRequest<'_>,
) -> Result<MemoryArchiveResult, MemoryIndexError> {
    archive::archive(request)
}
