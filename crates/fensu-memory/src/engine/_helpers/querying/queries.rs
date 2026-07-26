//! Validation, isolation, execution, and collection for memory queries.

use std::path::Path;

use rusqlite::{params, Connection, Rows};

use crate::engine::_helpers::querying::query_values;
use crate::engine::constants;
use crate::engine::errors::MemoryIndexError;
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
    let connection = Connection::open_in_memory()
        .map_err(|error| MemoryIndexError::sqlite("open isolated memory query", error))?;
    let database_value = database_path.to_string_lossy().into_owned();
    connection
        .execute("ATTACH DATABASE ?1 AS memory", params![database_value])
        .map_err(|error| MemoryIndexError::sqlite("attach read-only memory index", error))?;
    connection
        .execute_batch("PRAGMA query_only = ON; PRAGMA trusted_schema = OFF;")
        .map_err(|error| MemoryIndexError::sqlite("configure read-only memory query", error))?;
    execute(&connection, &wrapped_sql, limit)
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
        "SELECT * FROM ({query}) AS fensu_memory_query LIMIT {}",
        limit + 1
    ))
}

fn execute(
    connection: &Connection,
    wrapped_sql: &str,
    limit: usize,
) -> Result<MemoryQueryResult, MemoryIndexError> {
    let mut statement = connection
        .prepare(wrapped_sql)
        .map_err(|error| MemoryIndexError::sqlite("prepare read-only memory query", error))?;
    let column_count = statement.column_count();
    if column_count > constants::MAX_QUERY_COLUMNS {
        return Err(MemoryIndexError::TooManyQueryColumns {
            actual: column_count,
            maximum: constants::MAX_QUERY_COLUMNS,
        });
    }
    let columns = statement
        .column_names()
        .iter()
        .map(|name| (*name).to_owned())
        .collect::<Vec<String>>();
    let types = vec![constants::QUERY_NULL_TYPE.to_owned(); column_count];
    let mut rows = statement
        .query([])
        .map_err(|error| MemoryIndexError::sqlite("execute read-only memory query", error))?;
    RowCollector {
        rows: &mut rows,
        columns,
        types,
        column_count,
        limit,
        approximate_bytes: 0,
        result_rows: Vec::new(),
    }
    .collect()
}

struct RowCollector<'rows, 'statement> {
    rows: &'rows mut Rows<'statement>,
    columns: Vec<String>,
    types: Vec<String>,
    column_count: usize,
    limit: usize,
    approximate_bytes: usize,
    result_rows: Vec<Vec<MemoryQueryValue>>,
}

impl RowCollector<'_, '_> {
    fn collect(mut self) -> Result<MemoryQueryResult, MemoryIndexError> {
        self.approximate_bytes = metadata_bytes(&self.columns, &self.types);
        enforce_result_size(self.approximate_bytes)?;
        while let Some(row) = self
            .rows
            .next()
            .map_err(|error| MemoryIndexError::sqlite("read memory query row", error))?
        {
            let mut values = Vec::with_capacity(self.column_count);
            for (index, type_name) in self.types.iter_mut().enumerate() {
                let value = row.get_ref(index).map_err(|error| {
                    MemoryIndexError::sqlite("decode memory query value", error)
                })?;
                if type_name == constants::QUERY_NULL_TYPE {
                    *type_name = query_values::type_name(value).to_owned();
                }
                let encoded = query_values::encode(value);
                if self.result_rows.len() < self.limit {
                    self.approximate_bytes = self
                        .approximate_bytes
                        .saturating_add(query_values::approximate_bytes(&encoded));
                    enforce_result_size(self.approximate_bytes)?;
                }
                values.push(encoded);
            }
            self.result_rows.push(values);
        }
        let truncated = self.result_rows.len() > self.limit;
        if truncated {
            self.result_rows.pop();
        }
        Ok(MemoryQueryResult {
            columns: self.columns,
            types: self.types,
            rows: self.result_rows,
            truncated,
        })
    }
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
