//! SQLite connection identity and cache-path safety.

use std::fs;
use std::path::{Component, Path, PathBuf};
use std::time::Duration;

use rusqlite::{Connection, OpenFlags, OptionalExtension};

use crate::cache::constants::{
    APPLICATION_ID, BUSY_TIMEOUT_MS, CACHE_RELATIVE_PATH, STORAGE_SCHEMA_VERSION,
};

const CREATE_RECORDS_SQL: &str = "CREATE TABLE records (key TEXT PRIMARY KEY NOT NULL, kind TEXT NOT NULL, data BLOB NOT NULL) WITHOUT ROWID";

pub(crate) fn database_path(repo_root: &Path) -> PathBuf {
    repo_root.join(CACHE_RELATIVE_PATH)
}

pub(crate) fn readable_connection(repo_root: &Path) -> Option<Connection> {
    let database = database_path(repo_root);
    if !database_is_readable(repo_root, &database) {
        return None;
    }
    let Ok(connection) = Connection::open_with_flags(&database, OpenFlags::SQLITE_OPEN_READ_ONLY)
    else {
        return None;
    };
    let Ok(()) = connection.busy_timeout(Duration::from_millis(BUSY_TIMEOUT_MS)) else {
        return None;
    };
    let Ok(()) = connection.execute_batch("PRAGMA query_only = ON; BEGIN") else {
        return None;
    };
    Some(connection)
}

pub(crate) fn writable_connection(repo_root: &Path) -> Option<Connection> {
    let database = database_path(repo_root);
    prepare_database_parent(repo_root, &database)?;
    if database.exists() && !database_is_readable(repo_root, &database) {
        return None;
    }
    let Ok(connection) = Connection::open(&database) else {
        return None;
    };
    let Ok(()) = connection.busy_timeout(Duration::from_millis(BUSY_TIMEOUT_MS)) else {
        return None;
    };
    let Ok(journal_mode): Result<String, _> =
        connection.query_row("PRAGMA journal_mode", [], |row| row.get(0))
    else {
        return None;
    };
    let active_mode = if journal_mode.eq_ignore_ascii_case("wal") {
        journal_mode
    } else {
        let Ok(mode) = connection.query_row("PRAGMA journal_mode = WAL", [], |row| row.get(0))
        else {
            return None;
        };
        mode
    };
    if !active_mode.eq_ignore_ascii_case("wal") {
        return None;
    }
    let Ok(()) = connection.execute_batch("PRAGMA synchronous = NORMAL") else {
        return None;
    };
    Some(connection)
}

pub(crate) fn begin_writable_transaction(connection: &Connection) -> Option<()> {
    let Ok(()) = connection.execute_batch("BEGIN IMMEDIATE") else {
        return None;
    };
    if database_is_uninitialized(connection) {
        let Ok(_) = connection.execute(CREATE_RECORDS_SQL, []) else {
            return None;
        };
        let Ok(()) = connection.execute_batch(&format!(
            "PRAGMA application_id = {APPLICATION_ID}; PRAGMA user_version = {STORAGE_SCHEMA_VERSION}"
        )) else {
            return None;
        };
        return Some(());
    }
    database_identity_is_current(connection).then_some(())
}

pub(crate) fn database_identity_is_current(connection: &Connection) -> bool {
    let Ok(application_id) =
        connection.query_row("PRAGMA application_id", [], |row| row.get::<_, i32>(0))
    else {
        return false;
    };
    let Ok(user_version) =
        connection.query_row("PRAGMA user_version", [], |row| row.get::<_, i32>(0))
    else {
        return false;
    };
    let Ok(mut statement) = connection.prepare("PRAGMA table_info(records)") else {
        return false;
    };
    let Ok(rows) = statement.query_map([], |row| {
        Ok((
            row.get::<_, String>(1)?,
            row.get::<_, String>(2)?,
            row.get::<_, i32>(3)?,
            row.get::<_, i32>(5)?,
        ))
    }) else {
        return false;
    };
    let Ok(columns) = rows.collect::<Result<Vec<_>, _>>() else {
        return false;
    };
    application_id == APPLICATION_ID
        && user_version == STORAGE_SCHEMA_VERSION
        && columns
            == vec![
                ("key".to_owned(), "TEXT".to_owned(), 1, 1),
                ("kind".to_owned(), "TEXT".to_owned(), 1, 0),
                ("data".to_owned(), "BLOB".to_owned(), 1, 0),
            ]
}

fn prepare_database_parent(repo_root: &Path, database: &Path) -> Option<()> {
    let relative_parent = Path::new(CACHE_RELATIVE_PATH).parent()?;
    let mut current = repo_root.to_path_buf();
    for component in relative_parent.components() {
        let Component::Normal(part) = component else {
            return None;
        };
        current.push(part);
        match fs::symlink_metadata(&current) {
            Ok(metadata) if metadata.file_type().is_symlink() || !metadata.is_dir() => return None,
            Ok(_) => {}
            Err(error) if error.kind() == std::io::ErrorKind::NotFound => {
                if fs::create_dir(&current).is_err() {
                    let Ok(metadata) = fs::symlink_metadata(&current) else {
                        return None;
                    };
                    if metadata.file_type().is_symlink() || !metadata.is_dir() {
                        return None;
                    }
                }
            }
            Err(_) => return None,
        }
    }
    (database.parent() == Some(current.as_path())).then_some(())
}

pub(crate) fn database_is_readable(repo_root: &Path, database: &Path) -> bool {
    let Ok(metadata) = fs::symlink_metadata(database) else {
        return false;
    };
    if metadata.file_type().is_symlink() || !metadata.is_file() {
        return false;
    }
    let Some(parent) = Path::new(CACHE_RELATIVE_PATH).parent() else {
        return false;
    };
    let mut current = repo_root.to_path_buf();
    for component in parent.components() {
        let Component::Normal(part) = component else {
            return false;
        };
        current.push(part);
        let Ok(metadata) = fs::symlink_metadata(&current) else {
            return false;
        };
        if metadata.file_type().is_symlink() || !metadata.is_dir() {
            return false;
        }
    }
    true
}

fn database_is_uninitialized(connection: &Connection) -> bool {
    let Ok(application_id) =
        connection.query_row("PRAGMA application_id", [], |row| row.get::<_, i32>(0))
    else {
        return false;
    };
    let Ok(user_version) =
        connection.query_row("PRAGMA user_version", [], |row| row.get::<_, i32>(0))
    else {
        return false;
    };
    let table = match connection
        .query_row(
            "SELECT name FROM sqlite_schema WHERE type = 'table' AND name NOT LIKE 'sqlite_%' LIMIT 1",
            [],
            |row| row.get::<_, String>(0),
        )
        .optional()
    {
        Ok(value) => value,
        Err(_) => return false,
    };
    application_id == 0 && user_version == 0 && table.is_none()
}
