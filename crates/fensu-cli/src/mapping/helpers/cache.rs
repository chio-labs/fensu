use std::fs;
use std::path::Path;
use std::time::Duration;

use rusqlite::{params, Connection, OptionalExtension};
use serde::{Deserialize, Serialize};
use sha2::{Digest, Sha256};

use crate::mapping::models::{MapCacheStats, ProjectIndex, SourceSnapshot};

const DATABASE: &str = ".fensu/cache/v4.db";
const APPLICATION_ID: i32 = 0x5354_5241;
const PREFIX: &str = "native/mapping/v2/";
const MANIFEST_KEY: &str = "native/mapping/v2/manifest";
const MANIFEST_KIND: &str = "native-map-manifest-v2";
const FILE_KIND: &str = "native-map-file-v2";
const CONTRACT: &str = "native-map-v2-ruff-py312";

#[derive(Deserialize, Serialize)]
struct CacheRecord<T> {
    identity: String,
    payload: T,
    payload_fingerprint: String,
}

pub(crate) struct CacheGeneration {
    pub(crate) project_identity: String,
    pub(crate) file_identities: Vec<String>,
}

pub(crate) fn generation(snapshots: &[SourceSnapshot]) -> CacheGeneration {
    let file_identities = snapshots.iter().map(file_identity).collect::<Vec<_>>();
    let mut digest = Sha256::new();
    digest.update(CONTRACT.as_bytes());
    for identity in &file_identities {
        digest.update(identity.as_bytes());
        digest.update([0]);
    }
    CacheGeneration {
        project_identity: format!("{:x}", digest.finalize()),
        file_identities,
    }
}

pub(crate) fn manifest_hit(root: &Path, generation: &CacheGeneration) -> bool {
    let Some(bytes) = read_record(root, MANIFEST_KEY, MANIFEST_KIND) else {
        return false;
    };
    let Ok(record) = serde_json::from_slice::<CacheRecord<Vec<String>>>(&bytes) else {
        return false;
    };
    record.identity == generation.project_identity
        && record.payload == generation.file_identities
        && fingerprint(&record.identity, &record.payload).as_deref()
            == Some(record.payload_fingerprint.as_str())
}

pub(crate) fn read_file(root: &Path, identity: &str) -> Option<ProjectIndex> {
    let key = file_key(identity);
    let bytes = read_record(root, &key, FILE_KIND)?;
    let record = serde_json::from_slice::<CacheRecord<ProjectIndex>>(&bytes).ok()?;
    if record.identity != identity
        || fingerprint(&record.identity, &record.payload).as_deref()
            != Some(record.payload_fingerprint.as_str())
    {
        return None;
    }
    Some(record.payload)
}

pub(crate) fn publish(
    root: &Path,
    generation: &CacheGeneration,
    files: &[(String, ProjectIndex)],
) -> bool {
    let path = root.join(DATABASE);
    let Some(parent) = path.parent() else {
        return false;
    };
    if fs::create_dir_all(parent).is_err() {
        return false;
    }
    let Ok(mut connection) = Connection::open(path) else {
        return false;
    };
    if connection
        .busy_timeout(Duration::from_millis(1000))
        .is_err()
        || initialize(&connection).is_err()
    {
        return false;
    }
    let Ok(transaction) = connection.transaction() else {
        return false;
    };
    for (identity, index) in files {
        let Some(bytes) = encode_record(identity, index) else {
            return false;
        };
        if transaction
            .execute(
                "INSERT INTO records(key,kind,data) VALUES (?,?,?) ON CONFLICT(key) DO UPDATE SET kind=excluded.kind,data=excluded.data",
                params![file_key(identity), FILE_KIND, bytes],
            )
            .is_err()
        {
            return false;
        }
    }
    let Some(manifest) = encode_record(&generation.project_identity, &generation.file_identities)
    else {
        return false;
    };
    if transaction
        .execute(
            "INSERT INTO records(key,kind,data) VALUES (?,?,?) ON CONFLICT(key) DO UPDATE SET kind=excluded.kind,data=excluded.data",
            params![MANIFEST_KEY, MANIFEST_KIND, manifest],
        )
        .is_err()
    {
        return false;
    }
    let retained = generation
        .file_identities
        .iter()
        .map(|identity| file_key(identity))
        .collect::<Vec<_>>();
    let Ok(mut statement) = transaction.prepare("SELECT key FROM records WHERE key LIKE ?") else {
        return false;
    };
    let Ok(rows) = statement.query_map([format!("{PREFIX}files/%")], |row| row.get::<_, String>(0))
    else {
        return false;
    };
    let stale = rows
        .filter_map(Result::ok)
        .filter(|key| !retained.contains(key))
        .collect::<Vec<_>>();
    drop(statement);
    for key in stale {
        if transaction
            .execute("DELETE FROM records WHERE key = ?", [key])
            .is_err()
        {
            return false;
        }
    }
    transaction.commit().is_ok()
}

pub(crate) fn stats_text(stats: MapCacheStats) -> String {
    let status = if stats.manifest_hit { "hit" } else { "miss" };
    format!(
        "Map cache: manifest={status} parsed_files={} reused_file_records={} writes={} storage_failed={} internal_error={}\n",
        stats.parsed_files,
        stats.reused_file_records,
        stats.writes,
        stats.storage_failed,
        stats.internal_error,
    )
}

fn file_identity(snapshot: &SourceSnapshot) -> String {
    let mut digest = Sha256::new();
    digest.update(CONTRACT.as_bytes());
    digest.update(snapshot.relative_path.as_bytes());
    digest.update([0]);
    digest.update(snapshot.module_name.as_bytes());
    digest.update([0]);
    digest.update(snapshot.import_root_identity.as_bytes());
    digest.update([0]);
    digest.update(snapshot.source_fingerprint.as_bytes());
    format!("{:x}", digest.finalize())
}

fn file_key(identity: &str) -> String {
    format!("{PREFIX}files/{identity}")
}

fn read_record(root: &Path, key: &str, kind: &str) -> Option<Vec<u8>> {
    let connection = Connection::open_with_flags(
        root.join(DATABASE),
        rusqlite::OpenFlags::SQLITE_OPEN_READ_ONLY,
    )
    .ok()?;
    if !valid_database(&connection) {
        return None;
    }
    connection
        .query_row(
            "SELECT data FROM records WHERE key = ? AND kind = ?",
            params![key, kind],
            |row| row.get::<_, Vec<u8>>(0),
        )
        .optional()
        .ok()?
}

fn encode_record<T: Serialize>(identity: &str, payload: &T) -> Option<Vec<u8>> {
    serde_json::to_vec(&CacheRecord {
        identity: identity.to_owned(),
        payload,
        payload_fingerprint: fingerprint(identity, payload)?,
    })
    .ok()
}

fn fingerprint<T: Serialize>(identity: &str, payload: &T) -> Option<String> {
    let encoded = serde_json::to_vec(&(identity, payload)).ok()?;
    Some(format!("{:x}", Sha256::digest(encoded)))
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
