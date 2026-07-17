//! Read-only aggregate queries for compact memory rendering.

use std::path::Path;

use duckdb::{AccessMode, Config, Connection};

use crate::engine::errors::MemoryIndexError;
use crate::engine::models::MemoryOverview;

const OVERVIEW_SQL: &str = r#"
SELECT
    count(*) FILTER (WHERE archive_state = 'active' AND artifact_kind = 'task' AND lifecycle = 'not-started'),
    count(*) FILTER (WHERE archive_state = 'active' AND artifact_kind = 'task' AND lifecycle = 'in-progress'),
    count(*) FILTER (WHERE archive_state = 'active' AND artifact_kind = 'task' AND lifecycle = 'completed'),
    count(*) FILTER (WHERE archive_state = 'active' AND artifact_kind = 'task' AND lifecycle = 'cancelled'),
    count(*) FILTER (WHERE archive_state = 'active' AND artifact_kind = 'task' AND lifecycle = 'superseded'),
    count(*) FILTER (WHERE archive_state = 'active' AND artifact_kind = 'note'),
    count(*) FILTER (WHERE archive_state = 'active' AND artifact_kind = 'decision'),
    count(*) FILTER (WHERE archive_state = 'active' AND artifact_kind = 'skill'),
    count(*) FILTER (WHERE archive_state = 'archived' AND artifact_kind = 'task'),
    count(*) FILTER (WHERE archive_state = 'archived' AND artifact_kind != 'task'),
    count(*),
    (SELECT count(*) FROM sections)
FROM documents
"#;

pub(crate) fn read(database_path: &Path) -> Result<MemoryOverview, MemoryIndexError> {
    if !database_path.is_file() {
        return Err(MemoryIndexError::DatabaseNotFound(
            database_path.to_path_buf(),
        ));
    }
    let config = Config::default()
        .access_mode(AccessMode::ReadOnly)
        .map_err(|error| MemoryIndexError::duckdb("configure read-only memory overview", error))?;
    let connection = Connection::open_with_flags(database_path, config)
        .map_err(|error| MemoryIndexError::duckdb("open read-only memory overview", error))?;
    let result = connection
        .query_row(OVERVIEW_SQL, [], |row| {
            Ok(MemoryOverview {
                not_started_task_count: count(row, 0)?,
                in_progress_task_count: count(row, 1)?,
                completed_task_count: count(row, 2)?,
                cancelled_task_count: count(row, 3)?,
                superseded_task_count: count(row, 4)?,
                active_note_count: count(row, 5)?,
                active_decision_count: count(row, 6)?,
                active_skill_count: count(row, 7)?,
                archived_task_count: count(row, 8)?,
                archived_knowledge_count: count(row, 9)?,
                document_count: count(row, 10)?,
                section_count: count(row, 11)?,
            })
        })
        .map_err(|error| MemoryIndexError::duckdb("read memory overview", error));
    let close_result = connection
        .close()
        .map_err(|(_, error)| MemoryIndexError::duckdb("close read-only memory overview", error));
    match result {
        Ok(overview) => {
            close_result?;
            Ok(overview)
        }
        Err(error) => Err(error),
    }
}

fn count(row: &duckdb::Row<'_>, index: usize) -> Result<usize, duckdb::Error> {
    row.get::<_, i64>(index).map(|value| value as usize)
}
