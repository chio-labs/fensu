use std::collections::HashMap;
use std::fs;
use std::path::Path;
use std::time::Duration;

use rusqlite::{params, Connection, OptionalExtension};

use crate::models::{CachedOutput, ScopedSource};

const DATABASE: &str = ".fensu/cache/v4.db";
const APPLICATION_ID: i32 = 0x5354_5241;
const COLOR_OUTPUT_KEY: &str = "native/check-output/color";
const PLAIN_OUTPUT_KEY: &str = "native/check-output/plain";

pub(crate) fn read(
    root: &Path,
    identity: &str,
    sources: &[ScopedSource],
    color: bool,
) -> Option<CachedOutput> {
    let connection = Connection::open_with_flags(
        root.join(DATABASE),
        rusqlite::OpenFlags::SQLITE_OPEN_READ_ONLY,
    )
    .ok()?;
    if !valid_database(&connection) {
        return None;
    }
    let data = connection
        .query_row(
            "SELECT data FROM records WHERE key = ? AND kind = 'check_output'",
            [output_key(color)],
            |row| row.get::<_, Vec<u8>>(0),
        )
        .optional()
        .ok()??;
    let output: CachedOutput = serde_json::from_slice(&data).ok()?;
    if output.identity != identity || output.file_count != sources.len() {
        return None;
    }
    let mut statement = connection
        .prepare("SELECT key,data FROM records WHERE key LIKE 'native/file/%'")
        .ok()?;
    let stored = statement
        .query_map([], |row| {
            Ok((row.get::<_, String>(0)?, row.get::<_, Vec<u8>>(1)?))
        })
        .ok()?
        .collect::<Result<HashMap<_, _>, _>>()
        .ok()?;
    if stored.len() != sources.len() {
        return None;
    }
    for source in sources {
        let key = format!("native/file/{}", source.repository_path);
        let value: serde_json::Value = serde_json::from_slice(stored.get(&key)?).ok()?;
        if value.get("fingerprint")?.as_str()? != source.fingerprint {
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
    let mut current = Vec::new();
    for source in sources {
        let key = format!("native/file/{}", source.repository_path);
        let Ok(data) = serde_json::to_vec(&serde_json::json!({"fingerprint": source.fingerprint}))
        else {
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
    if connection
        .execute(
            "INSERT INTO records(key,kind,data) VALUES (?,'check_output',?) ON CONFLICT(key) DO UPDATE SET kind=excluded.kind,data=excluded.data",
            params![output_key(color), data],
        )
        .is_err()
    {
        let _ = connection.execute_batch("ROLLBACK");
        return false;
    }
    if let Ok(mut statement) =
        connection.prepare("SELECT key FROM records WHERE key LIKE 'native/file/%'")
    {
        let stale = statement
            .query_map([], |row| row.get::<_, String>(0))
            .ok()
            .into_iter()
            .flatten()
            .filter_map(Result::ok)
            .filter(|key| !current.contains(key))
            .collect::<Vec<_>>();
        for key in stale {
            let _ = connection.execute("DELETE FROM records WHERE key = ?", [key]);
        }
    }
    connection.execute_batch("COMMIT").is_ok()
}

fn initialize(connection: &Connection) -> rusqlite::Result<()> {
    connection.execute_batch(&format!(
        "PRAGMA journal_mode=WAL; PRAGMA synchronous=NORMAL; CREATE TABLE IF NOT EXISTS records (key TEXT PRIMARY KEY NOT NULL, kind TEXT NOT NULL, data BLOB NOT NULL) WITHOUT ROWID; PRAGMA application_id={APPLICATION_ID}; PRAGMA user_version=1;"
    ))
}

fn valid_database(connection: &Connection) -> bool {
    connection
        .query_row("PRAGMA application_id", [], |row| row.get::<_, i32>(0))
        .ok()
        == Some(APPLICATION_ID)
}

fn output_key(color: bool) -> &'static str {
    if color {
        COLOR_OUTPUT_KEY
    } else {
        PLAIN_OUTPUT_KEY
    }
}
