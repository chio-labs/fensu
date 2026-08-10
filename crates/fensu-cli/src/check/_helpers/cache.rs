use std::fs;
use std::path::Path;
use std::time::Duration;

use rusqlite::{params, Connection, OptionalExtension};

use crate::models::{CachedOutput, ScopedSource};

const DATABASE: &str = ".fensu/cache/v4.db";
const APPLICATION_ID: i32 = 0x5354_5241;
const CACHE_SCHEMA_VERSION: i32 = 2;
const MAX_CACHE_NAMESPACES: i64 = 16;

pub(crate) fn read(
    root: &Path,
    identity: &str,
    sources: &[ScopedSource],
    color: bool,
) -> Option<CachedOutput> {
    let Ok(connection) = Connection::open_with_flags(
        root.join(DATABASE),
        rusqlite::OpenFlags::SQLITE_OPEN_READ_ONLY,
    ) else {
        return None;
    };
    if !valid_database(&connection) {
        return None;
    }
    let namespace = surface_namespace(sources);
    let key = output_key(&namespace, color, identity);
    let Ok(data) = connection
        .query_row(
            "SELECT data FROM records WHERE key = ? AND kind = 'check_output'",
            [key],
            |row| row.get::<_, Vec<u8>>(0),
        )
        .optional()
    else {
        return None;
    };
    let data = data?;
    let Ok(output) = serde_json::from_slice::<CachedOutput>(&data) else {
        return None;
    };
    if output.identity != identity || output.file_count != sources.len() {
        return None;
    }
    for source in sources {
        let key = source_key(&namespace, source);
        let Ok(data) = connection
            .query_row(
                "SELECT data FROM records WHERE key = ? AND kind = 'file_result'",
                [key],
                |row| row.get::<_, Vec<u8>>(0),
            )
            .optional()
        else {
            return None;
        };
        let data = data?;
        let Ok(value) = serde_json::from_slice::<serde_json::Value>(&data) else {
            return None;
        };
        if value.get("fingerprint")?.as_str()? != source.fingerprint
            || value.get("analyzer")?.as_str()? != source.analyzer.to_string()
            || value.get("target")?.as_str()? != source.target_identity
            || value.get("parser_contract")?.as_str()? != source.parser_contract
            || value.get("repository_path")?.as_str()? != source.repository_path
        {
            return None;
        }
    }
    Some(output)
}

pub(crate) fn write(
    root: &Path,
    output: &CachedOutput,
    sources: &[ScopedSource],
    color: bool,
) -> bool {
    let path = root.join(DATABASE);
    let Some(parent) = path.parent() else {
        return false;
    };
    if fs::create_dir_all(parent).is_err() {
        return false;
    }
    let Ok(connection) = Connection::open(path) else {
        return false;
    };
    if connection
        .busy_timeout(Duration::from_millis(1000))
        .is_err()
        || initialize(&connection).is_err()
        || connection.execute_batch("BEGIN IMMEDIATE").is_err()
    {
        return false;
    }
    let namespace = surface_namespace(sources);
    let mut current: Vec<String> = Vec::with_capacity(sources.len());
    for source in sources {
        let key = source_key(&namespace, source);
        let Ok(data) = serde_json::to_vec(&serde_json::json!({
            "analyzer": source.analyzer.to_string(),
            "target": source.target_identity,
            "parser_contract": source.parser_contract,
            "repository_path": source.repository_path,
            "fingerprint": source.fingerprint,
        })) else {
            return false;
        };
        if connection
            .execute(
                "INSERT INTO records(key,kind,data) VALUES (?,'file_result',?) ON CONFLICT(key) DO UPDATE SET kind=excluded.kind,data=excluded.data",
                params![key, data],
            )
            .is_err()
        {
            let _ = connection.execute_batch("ROLLBACK");
            return false;
        }
        current.push(key);
    }
    let Ok(data) = serde_json::to_vec(output) else {
        return false;
    };
    let output_record_key = output_key(&namespace, color, &output.identity);
    if connection
        .execute(
            "INSERT INTO records(key,kind,data) VALUES (?,'check_output',?) ON CONFLICT(key) DO UPDATE SET kind=excluded.kind,data=excluded.data",
            params![output_record_key, data],
        )
        .is_err()
    {
        let _ = connection.execute_batch("ROLLBACK");
        return false;
    }
    if prune_namespace(&connection, &namespace, &output_record_key, &current).is_err()
        || touch_namespace(&connection, &namespace).is_err()
        || prune_old_namespaces(&connection).is_err()
    {
        let _ = connection.execute_batch("ROLLBACK");
        return false;
    }
    match connection.execute_batch("COMMIT") {
        Ok(()) => true,
        Err(_) => false,
    }
}

fn initialize(connection: &Connection) -> rusqlite::Result<()> {
    connection.execute_batch(&format!(
        "PRAGMA journal_mode=WAL; PRAGMA synchronous=NORMAL; CREATE TABLE IF NOT EXISTS records (key TEXT PRIMARY KEY NOT NULL, kind TEXT NOT NULL, data BLOB NOT NULL) WITHOUT ROWID; CREATE TABLE IF NOT EXISTS cache_namespaces (namespace TEXT PRIMARY KEY NOT NULL, touched INTEGER NOT NULL) WITHOUT ROWID; PRAGMA application_id={APPLICATION_ID};"
    ))?;
    let version = connection.query_row("PRAGMA user_version", [], |row| row.get::<_, i32>(0))?;
    if version < CACHE_SCHEMA_VERSION {
        connection.execute(
            "DELETE FROM records WHERE key LIKE 'native/file/%' OR key LIKE 'native/check-output/%'",
            [],
        )?;
        connection.execute_batch(&format!("PRAGMA user_version={CACHE_SCHEMA_VERSION};"))?;
    }
    Ok(())
}

fn valid_database(connection: &Connection) -> bool {
    match connection.query_row("PRAGMA application_id", [], |row| row.get::<_, i32>(0)) {
        Ok(application_id) => application_id == APPLICATION_ID,
        Err(_) => false,
    }
}

fn output_key(namespace: &str, color: bool, identity: &str) -> String {
    let style = if color { "color" } else { "plain" };
    format!("native/surface/{namespace}/output/{style}/{identity}")
}

fn source_key(namespace: &str, source: &ScopedSource) -> String {
    let identity = serde_json::to_vec(&serde_json::json!([
        source.analyzer.to_string(),
        source.target_identity,
        source.parser_contract,
        source.repository_path,
    ]))
    .unwrap_or_default();
    format!(
        "native/surface/{namespace}/file/{}",
        crate::check::_helpers::policy::hex_digest(&identity)
    )
}

fn surface_namespace(sources: &[ScopedSource]) -> String {
    let identities = sources
        .iter()
        .map(|source| {
            serde_json::json!([
                source.analyzer.to_string(),
                source.target_identity,
                source.parser_contract,
                source.repository_path,
                source.target_path,
            ])
        })
        .collect::<Vec<_>>();
    let encoded = serde_json::to_vec(&identities).unwrap_or_default();
    crate::check::_helpers::policy::hex_digest(&encoded)
}

fn prune_namespace(
    connection: &Connection,
    namespace: &str,
    output: &str,
    current_files: &[String],
) -> rusqlite::Result<()> {
    let prefix = format!("native/surface/{namespace}/");
    let output_prefix = output
        .rsplit_once('/')
        .map_or_else(String::new, |(value, _)| format!("{value}/"));
    let mut statement = connection.prepare("SELECT key FROM records WHERE key LIKE ?")?;
    let keys = statement
        .query_map([format!("{prefix}%")], |row| row.get::<_, String>(0))?
        .collect::<Result<Vec<_>, _>>()?;
    for key in keys {
        let stale_file = key.starts_with(&format!("{prefix}file/"))
            && !current_files.iter().any(|current| current == &key);
        let stale_output = key.starts_with(&output_prefix) && key != output;
        if stale_file || stale_output {
            connection.execute("DELETE FROM records WHERE key = ?", [key])?;
        }
    }
    Ok(())
}

fn touch_namespace(connection: &Connection, namespace: &str) -> rusqlite::Result<()> {
    connection.execute(
        "INSERT INTO cache_namespaces(namespace,touched) VALUES (?,(SELECT COALESCE(MAX(touched),0)+1 FROM cache_namespaces)) ON CONFLICT(namespace) DO UPDATE SET touched=(SELECT COALESCE(MAX(touched),0)+1 FROM cache_namespaces)",
        [namespace],
    )?;
    Ok(())
}

fn prune_old_namespaces(connection: &Connection) -> rusqlite::Result<()> {
    let mut statement = connection.prepare(
        "SELECT namespace FROM cache_namespaces ORDER BY touched DESC, namespace DESC LIMIT -1 OFFSET ?",
    )?;
    let stale = statement
        .query_map([MAX_CACHE_NAMESPACES], |row| row.get::<_, String>(0))?
        .collect::<Result<Vec<_>, _>>()?;
    for namespace in stale {
        connection.execute(
            "DELETE FROM records WHERE key LIKE ?",
            [format!("native/surface/{namespace}/%")],
        )?;
        connection.execute(
            "DELETE FROM cache_namespaces WHERE namespace = ?",
            [namespace],
        )?;
    }
    Ok(())
}
