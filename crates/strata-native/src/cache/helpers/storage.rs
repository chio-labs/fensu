//! Fail-soft transactional SQLite cache storage.

use std::collections::{HashMap, HashSet};
use std::path::{Component, Path};

use rusqlite::{params, params_from_iter, Connection};

use crate::cache::constants::READ_CHUNK_SIZE;
use crate::cache::helpers::database::{
    begin_writable_transaction, database_identity_is_current, database_is_readable, database_path,
    readable_connection, writable_connection,
};
use crate::cache::helpers::records::decode_record;
use crate::cache::models::{CacheMetrics, CacheMutation, DecodedRecord, EncodedWrite};

const UPSERT_RECORD_SQL: &str = "INSERT INTO records(key, kind, data) VALUES (?, ?, ?) ON CONFLICT(key) DO UPDATE SET kind = excluded.kind, data = excluded.data";

pub(crate) fn read_records(
    repo_root: &Path,
    reads: &[(String, String)],
    maximum_decoded_bytes: usize,
) -> Option<(Vec<Option<DecodedRecord>>, CacheMetrics)> {
    if reads.iter().any(|(key, _)| !valid_key(key)) {
        return None;
    }
    let database = database_path(repo_root);
    if !database_is_readable(repo_root, &database) {
        return Some((empty_records(reads.len()), CacheMetrics::default()));
    }
    let connection = readable_connection(repo_root)?;
    let mut metrics = CacheMetrics {
        reads: reads.len(),
        ..CacheMetrics::default()
    };
    let rows = fetch_rows(
        &connection,
        &reads.iter().map(|(key, _)| key.clone()).collect::<Vec<_>>(),
        &mut metrics,
    )?;
    if !database_identity_is_current(&connection) {
        return Some((empty_records(reads.len()), metrics));
    }
    let records = reads
        .iter()
        .map(|(key, expected_kind)| {
            let (kind, data) = rows.get(key)?;
            if kind != expected_kind {
                return None;
            }
            decode_record(data, expected_kind, maximum_decoded_bytes)
        })
        .collect();
    Some((records, metrics))
}

pub(crate) fn write_records(repo_root: &Path, writes: &[EncodedWrite]) -> Option<CacheMetrics> {
    if writes.is_empty() {
        return Some(CacheMetrics::default());
    }
    valid_writes(writes).then_some(())?;
    let connection = writable_connection(repo_root)?;
    begin_writable_transaction(&connection)?;
    let mut metrics = CacheMetrics::default();
    if publish_writes(&connection, writes, &mut metrics).is_none() {
        let _ = connection.execute_batch("ROLLBACK");
        return None;
    }
    if connection.execute_batch("COMMIT").is_err() {
        let _ = connection.execute_batch("ROLLBACK");
        return None;
    }
    Some(metrics)
}

pub(crate) fn mutate_records<F>(
    repo_root: &Path,
    reads: &[(String, String)],
    maximum_decoded_bytes: usize,
    mutate: F,
) -> Option<(Option<CacheMutation>, CacheMetrics)>
where
    F: FnOnce(Vec<Option<DecodedRecord>>) -> Result<Option<CacheMutation>, ()>,
{
    if reads.iter().any(|(key, _)| !valid_key(key)) {
        return None;
    }
    let connection = writable_connection(repo_root)?;
    begin_writable_transaction(&connection)?;
    let mut metrics = CacheMetrics {
        reads: reads.len(),
        ..CacheMetrics::default()
    };
    let rows = fetch_rows(
        &connection,
        &reads.iter().map(|(key, _)| key.clone()).collect::<Vec<_>>(),
        &mut metrics,
    );
    let Some(rows) = rows else {
        let _ = connection.execute_batch("ROLLBACK");
        return None;
    };
    let records = reads
        .iter()
        .map(|(key, expected_kind)| {
            let (kind, data) = rows.get(key)?;
            if kind != expected_kind {
                return None;
            }
            decode_record(data, expected_kind, maximum_decoded_bytes)
        })
        .collect();
    let mutation = match mutate(records) {
        Ok(mutation) => mutation,
        Err(()) => {
            let _ = connection.execute_batch("ROLLBACK");
            return None;
        }
    };
    let Some(mutation) = mutation else {
        let _ = connection.execute_batch("ROLLBACK");
        return Some((None, metrics));
    };
    if apply_mutation(&connection, &mutation, &mut metrics).is_none() {
        let _ = connection.execute_batch("ROLLBACK");
        return None;
    }
    if connection.execute_batch("COMMIT").is_err() {
        let _ = connection.execute_batch("ROLLBACK");
        return None;
    }
    Some((Some(mutation), metrics))
}

fn fetch_rows(
    connection: &Connection,
    keys: &[String],
    metrics: &mut CacheMetrics,
) -> Option<HashMap<String, (String, Vec<u8>)>> {
    let mut rows_by_key = HashMap::new();
    for chunk in keys.chunks(READ_CHUNK_SIZE) {
        let placeholders = std::iter::repeat_n("?", chunk.len())
            .collect::<Vec<_>>()
            .join(",");
        let sql = format!("SELECT key, kind, data FROM records WHERE key IN ({placeholders})");
        let mut statement = connection.prepare(&sql).ok()?;
        let rows = statement
            .query_map(params_from_iter(chunk.iter()), |row| {
                Ok((row.get::<_, String>(0)?, row.get(1)?, row.get(2)?))
            })
            .ok()?;
        for row in rows {
            let (key, kind, data): (String, String, Vec<u8>) = row.ok()?;
            metrics.bytes_read += data.len();
            rows_by_key.insert(key, (kind, data));
        }
    }
    Some(rows_by_key)
}

fn publish_writes(
    connection: &Connection,
    writes: &[EncodedWrite],
    metrics: &mut CacheMetrics,
) -> Option<()> {
    for write in writes {
        let sql = if write.insert_only {
            "INSERT INTO records(key, kind, data) VALUES (?, ?, ?)"
        } else {
            UPSERT_RECORD_SQL
        };
        connection
            .execute(sql, params![write.key, write.kind, write.data])
            .ok()?;
    }
    metrics.writes += writes.len();
    metrics.bytes_written += writes.iter().map(|write| write.data.len()).sum::<usize>();
    Some(())
}

fn apply_mutation(
    connection: &Connection,
    mutation: &CacheMutation,
    metrics: &mut CacheMetrics,
) -> Option<()> {
    valid_writes(&mutation.writes).then_some(())?;
    mutation
        .swept_prefix
        .as_ref()
        .map(|prefix| valid_key(prefix))
        .unwrap_or(true)
        .then_some(())?;
    mutation
        .retained_paths
        .iter()
        .chain(mutation.deleted_paths.iter())
        .all(|path| valid_key(path))
        .then_some(())?;
    publish_writes(connection, &mutation.writes, metrics)?;
    let written = mutation
        .writes
        .iter()
        .map(|write| write.key.as_str())
        .collect::<HashSet<_>>();
    if let Some(prefix) = &mutation.swept_prefix {
        let retained = mutation
            .retained_paths
            .iter()
            .map(String::as_str)
            .chain(written.iter().copied())
            .collect::<HashSet<_>>();
        let pattern = format!("{prefix}/%");
        let mut statement = connection
            .prepare("SELECT key FROM records WHERE key LIKE ?")
            .ok()?;
        let keys = statement
            .query_map([pattern], |row| row.get::<_, String>(0))
            .ok()?
            .collect::<Result<Vec<_>, _>>()
            .ok()?;
        metrics.scans += keys.len();
        let doomed = keys
            .into_iter()
            .filter(|key| !retained.contains(key.as_str()))
            .collect::<Vec<_>>();
        delete_keys(connection, &doomed, metrics)?;
    }
    let doomed = mutation
        .deleted_paths
        .iter()
        .filter(|key| !written.contains(key.as_str()))
        .cloned()
        .collect::<HashSet<_>>()
        .into_iter()
        .collect::<Vec<_>>();
    delete_keys(connection, &doomed, metrics)
}

fn delete_keys(connection: &Connection, keys: &[String], metrics: &mut CacheMetrics) -> Option<()> {
    metrics.deletes += keys.len();
    for chunk in keys.chunks(READ_CHUNK_SIZE) {
        let placeholders = std::iter::repeat_n("?", chunk.len())
            .collect::<Vec<_>>()
            .join(",");
        connection
            .execute(
                &format!("DELETE FROM records WHERE key IN ({placeholders})"),
                params_from_iter(chunk.iter()),
            )
            .ok()?;
    }
    Some(())
}

fn valid_writes(writes: &[EncodedWrite]) -> bool {
    let mut keys = HashSet::new();
    writes
        .iter()
        .all(|write| valid_key(&write.key) && keys.insert(write.key.as_str()))
}

fn valid_key(key: &str) -> bool {
    !key.is_empty()
        && !Path::new(key).is_absolute()
        && Path::new(key)
            .components()
            .all(|component| matches!(component, Component::Normal(_)))
}

fn empty_records(count: usize) -> Vec<Option<DecodedRecord>> {
    std::iter::repeat_with(|| None).take(count).collect()
}
