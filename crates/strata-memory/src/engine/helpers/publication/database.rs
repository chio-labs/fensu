//! Transactional temporary-database construction and atomic replacement.

use std::ffi::OsString;
use std::fs;
use std::io;
use std::path::{Path, PathBuf};
use std::sync::atomic::{AtomicU64, Ordering};

use rusqlite::Connection;

use crate::corpus::models::MemoryCorpus;
use crate::engine::constants;
use crate::engine::errors::MemoryIndexError;
use crate::engine::helpers::publication::{documents, lists, references, sections, skills};
use crate::engine::models::IndexSummary;
use crate::graph::models::MemoryGraph;

static TEMPORARY_COUNTER: AtomicU64 = AtomicU64::new(0);

pub(crate) fn publish(
    corpus: &MemoryCorpus,
    graph: &MemoryGraph,
    database_path: &Path,
) -> Result<IndexSummary, MemoryIndexError> {
    let parent = database_parent(database_path)?;
    fs::create_dir_all(&parent).map_err(|error| {
        MemoryIndexError::filesystem("create database directory", parent.clone(), error)
    })?;
    let temporary_path = temporary_path(database_path, &parent)?;
    let journal_path = sidecar_path(&temporary_path, "-journal");
    let wal_path = sidecar_path(&temporary_path, "-wal");
    let shm_path = sidecar_path(&temporary_path, "-shm");
    let temporary_files: [&Path; 4] = [
        temporary_path.as_path(),
        journal_path.as_path(),
        wal_path.as_path(),
        shm_path.as_path(),
    ];
    let summary = match build_database(corpus, graph, &temporary_path) {
        Ok(summary) => summary,
        Err(error) => return Err(cleanup_files(error, &temporary_files)),
    };
    for sidecar in [&journal_path, &wal_path, &shm_path] {
        if let Err(error) = remove_if_exists(sidecar) {
            let failure = MemoryIndexError::filesystem(
                "remove temporary SQLite sidecar",
                sidecar.clone(),
                error,
            );
            return Err(cleanup_files(failure, &temporary_files));
        }
    }
    if let Err(error) = fs::rename(&temporary_path, database_path) {
        let failure = MemoryIndexError::filesystem(
            "publish memory index",
            database_path.to_path_buf(),
            error,
        );
        return Err(cleanup_files(failure, &temporary_files));
    }
    Ok(summary)
}

fn build_database(
    corpus: &MemoryCorpus,
    graph: &MemoryGraph,
    temporary_path: &Path,
) -> Result<IndexSummary, MemoryIndexError> {
    let mut connection = Connection::open(temporary_path)
        .map_err(|error| MemoryIndexError::sqlite("open temporary memory index", error))?;
    connection
        .execute_batch(
            "PRAGMA foreign_keys = ON; PRAGMA journal_mode = OFF; PRAGMA synchronous = OFF; PRAGMA temp_store = MEMORY;",
        )
        .map_err(|error| MemoryIndexError::sqlite("configure temporary memory index", error))?;
    let transaction = connection
        .transaction()
        .map_err(|error| MemoryIndexError::sqlite("begin memory index transaction", error))?;
    transaction
        .execute_batch(constants::MEMORY_SCHEMA_SQL)
        .map_err(|error| MemoryIndexError::sqlite("create memory schema", error))?;
    let document_count = documents::insert(&transaction, corpus)?;
    let section_count = sections::insert(&transaction, corpus)?;
    let (list_item_count, list_item_batch_count) = lists::insert(&transaction, corpus)?;
    let link_count = references::insert_links(&transaction, corpus, graph)?;
    let tag_count = references::insert_tags(&transaction, corpus)?;
    let skill_file_count = skills::insert(&transaction, corpus)?;
    transaction
        .commit()
        .map_err(|error| MemoryIndexError::sqlite("commit memory index transaction", error))?;
    connection
        .close()
        .map_err(|(_, error)| MemoryIndexError::sqlite("close temporary memory index", error))?;
    Ok(IndexSummary {
        document_count,
        section_count,
        list_item_count,
        list_item_batch_count,
        link_count,
        tag_count,
        skill_file_count,
        source_diagnostic_count: corpus.source_diagnostics.len(),
        corpus_diagnostic_count: corpus.diagnostics.len(),
        graph_diagnostic_count: graph.diagnostics.len(),
    })
}

fn database_parent(database_path: &Path) -> Result<PathBuf, MemoryIndexError> {
    if database_path.file_name().is_none() {
        return Err(MemoryIndexError::InvalidDatabasePath(
            database_path.to_path_buf(),
        ));
    }
    let parent = database_path.parent().unwrap_or_else(|| Path::new("."));
    if parent.as_os_str().is_empty() {
        Ok(PathBuf::from("."))
    } else {
        Ok(parent.to_path_buf())
    }
}

fn temporary_path(database_path: &Path, parent: &Path) -> Result<PathBuf, MemoryIndexError> {
    let file_name = database_path
        .file_name()
        .ok_or_else(|| MemoryIndexError::InvalidDatabasePath(database_path.to_path_buf()))?;
    let sequence = TEMPORARY_COUNTER.fetch_add(1, Ordering::Relaxed);
    let mut temporary_name = OsString::from(".");
    temporary_name.push(file_name);
    temporary_name.push(format!(
        ".strata-memory-{}-{sequence}.tmp",
        std::process::id()
    ));
    Ok(parent.join(temporary_name))
}

fn sidecar_path(database_path: &Path, suffix: &str) -> PathBuf {
    let mut value = database_path.as_os_str().to_os_string();
    value.push(suffix);
    PathBuf::from(value)
}

fn cleanup_files(mut original: MemoryIndexError, paths: &[&Path]) -> MemoryIndexError {
    for path in paths {
        if let Err(source) = remove_if_exists(path) {
            original = MemoryIndexError::Cleanup {
                path: path.to_path_buf(),
                source,
                original: Box::new(original),
            };
        }
    }
    original
}

fn remove_if_exists(path: &Path) -> Result<(), io::Error> {
    match fs::remove_file(path) {
        Ok(()) => Ok(()),
        Err(error) if error.kind() == io::ErrorKind::NotFound => Ok(()),
        Err(error) => Err(error),
    }
}
