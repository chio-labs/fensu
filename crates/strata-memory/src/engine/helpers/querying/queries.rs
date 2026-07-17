//! Validation, isolation, execution, and collection for memory queries.

use std::path::Path;

use duckdb::{AccessMode, Config, Connection, Rows};

use crate::engine::constants;
use crate::engine::errors::MemoryIndexError;
use crate::engine::helpers::querying::query_values;
use crate::engine::models::{MemoryQueryResult, MemoryQueryValue};

pub(crate) fn run(
    database_path: &Path,
    sql: &str,
    limit: usize,
) -> Result<MemoryQueryResult, MemoryIndexError> {
    let wrapped_sql = wrapped_sql(sql, limit)?;
    if !database_path.is_file() {
        return Err(MemoryIndexError::DatabaseNotFound(
            database_path.to_path_buf(),
        ));
    }
    let config = query_config()?;
    let connection = Connection::open_with_flags(database_path, config)
        .map_err(|error| MemoryIndexError::duckdb("open read-only memory index", error))?;
    let result = execute(&connection, &wrapped_sql, limit);
    let close_result = connection
        .close()
        .map_err(|(_, error)| MemoryIndexError::duckdb("close read-only memory index", error));
    match result {
        Ok(result) => {
            close_result?;
            Ok(result)
        }
        Err(error) => {
            let _close_result = close_result;
            Err(error)
        }
    }
}

fn wrapped_sql(sql: &str, limit: usize) -> Result<String, MemoryIndexError> {
    if !(constants::MIN_QUERY_LIMIT..=constants::MAX_QUERY_LIMIT).contains(&limit) {
        return Err(MemoryIndexError::InvalidQueryLimit {
            limit,
            minimum: constants::MIN_QUERY_LIMIT,
            maximum: constants::MAX_QUERY_LIMIT,
        });
    }
    let actual_bytes = sql.len();
    if actual_bytes > constants::MAX_QUERY_SQL_BYTES {
        return Err(MemoryIndexError::QueryTooLong {
            actual_bytes,
            maximum_bytes: constants::MAX_QUERY_SQL_BYTES,
        });
    }
    let trimmed = sql.trim();
    let query = trimmed.strip_suffix(';').unwrap_or(trimmed).trim_end();
    if query.is_empty() {
        return Err(MemoryIndexError::EmptyQuery);
    }
    Ok(format!(
        "SELECT * FROM ({query}) AS strata_memory_query LIMIT {}",
        limit + 1
    ))
}

fn query_config() -> Result<Config, MemoryIndexError> {
    Config::default()
        .access_mode(AccessMode::ReadOnly)
        .and_then(|config| config.enable_external_access(false))
        .and_then(|config| config.enable_autoload_extension(false))
        .and_then(|config| config.threads(1))
        .and_then(|config| config.max_memory(constants::QUERY_MAX_MEMORY))
        .and_then(|config| {
            config.with(
                "max_temp_directory_size",
                constants::QUERY_MAX_TEMP_DIRECTORY_SIZE,
            )
        })
        .map_err(|error| MemoryIndexError::duckdb("configure read-only memory query", error))
}

fn execute(
    connection: &Connection,
    wrapped_sql: &str,
    limit: usize,
) -> Result<MemoryQueryResult, MemoryIndexError> {
    let mut statement = connection
        .prepare(wrapped_sql)
        .map_err(|error| MemoryIndexError::duckdb("prepare read-only memory query", error))?;
    let mut rows = statement
        .query([])
        .map_err(|error| MemoryIndexError::duckdb("execute read-only memory query", error))?;
    let metadata = rows
        .as_ref()
        .ok_or(MemoryIndexError::QueryMetadataUnavailable)?;
    let column_count = metadata.column_count();
    if column_count > constants::MAX_QUERY_COLUMNS {
        return Err(MemoryIndexError::TooManyQueryColumns {
            actual: column_count,
            maximum: constants::MAX_QUERY_COLUMNS,
        });
    }
    let columns = metadata.column_names();
    let types = (0..column_count)
        .map(|index| format!("{:?}", metadata.column_logical_type(index)))
        .collect::<Vec<String>>();
    collect_rows(&mut rows, columns, types, column_count, limit)
}

fn collect_rows(
    rows: &mut Rows<'_>,
    columns: Vec<String>,
    types: Vec<String>,
    column_count: usize,
    limit: usize,
) -> Result<MemoryQueryResult, MemoryIndexError> {
    let mut approximate_bytes = metadata_bytes(&columns, &types);
    enforce_result_size(approximate_bytes)?;
    let mut result_rows: Vec<Vec<MemoryQueryValue>> = Vec::new();
    while let Some(row) = rows
        .next()
        .map_err(|error| MemoryIndexError::duckdb("read memory query row", error))?
    {
        let mut values = Vec::with_capacity(column_count);
        for index in 0..column_count {
            let owned = row
                .get(index)
                .map_err(|error| MemoryIndexError::duckdb("decode memory query value", error))?;
            let encoded = query_values::encode(owned, 0)?;
            if result_rows.len() < limit {
                approximate_bytes =
                    approximate_bytes.saturating_add(query_values::approximate_bytes(&encoded));
                enforce_result_size(approximate_bytes)?;
            }
            values.push(encoded);
        }
        result_rows.push(values);
    }
    let truncated = result_rows.len() > limit;
    if truncated {
        result_rows.pop();
    }
    Ok(MemoryQueryResult {
        columns,
        types,
        rows: result_rows,
        truncated,
    })
}

fn metadata_bytes(columns: &[String], types: &[String]) -> usize {
    columns.iter().map(String::len).sum::<usize>() + types.iter().map(String::len).sum::<usize>()
}

fn enforce_result_size(approximate_bytes: usize) -> Result<(), MemoryIndexError> {
    if approximate_bytes > constants::MAX_QUERY_RESULT_BYTES {
        return Err(MemoryIndexError::QueryResultTooLarge {
            approximate_bytes,
            maximum_bytes: constants::MAX_QUERY_RESULT_BYTES,
        });
    }
    Ok(())
}
