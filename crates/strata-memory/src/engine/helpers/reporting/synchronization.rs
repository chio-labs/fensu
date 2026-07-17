//! Read-only source comparison and atomic rebuild selection.

use std::collections::BTreeMap;
use std::path::Path;

use duckdb::{AccessMode, Config, Connection};

use crate::corpus::main::load_discovered_memory_corpus::load_discovered_memory_corpus;
use crate::engine::constants;
use crate::engine::errors::MemoryIndexError;
use crate::engine::helpers::publication::database;
use crate::engine::helpers::reporting::schema_metadata;
use crate::engine::models::{IndexSummary, SyncSummary};
use crate::graph::main::resolve_memory_graph::resolve_memory_graph;
use crate::source::models::DiscoveryResult;

#[derive(Clone, Debug, Eq, PartialEq)]
struct SourceFact {
    key: String,
    owner: String,
    path: String,
    content_sha256: String,
}

#[derive(Clone, Debug, Default, Eq, PartialEq)]
struct ChangeCounts {
    added: usize,
    changed: usize,
    moved: usize,
    removed: usize,
    unchanged: usize,
}

#[derive(Clone, Debug, Default, Eq, PartialEq)]
struct StoredIndex {
    documents: Vec<SourceFact>,
    skill_files: Vec<SourceFact>,
    document_count: usize,
    section_count: usize,
    link_count: usize,
}

struct DatabaseInspection {
    snapshot: Option<StoredIndex>,
    current: bool,
}

pub(crate) fn sync(
    discovery: DiscoveryResult,
    database_path: &Path,
) -> Result<SyncSummary, MemoryIndexError> {
    let inspection = inspect(database_path);
    let current_documents = document_facts(&discovery);
    let current_skill_files = skill_file_facts(&discovery);
    let stored = inspection.snapshot.unwrap_or_default();
    let mut changes = classify(&current_documents, &stored.documents, false);
    changes.add(classify(&current_skill_files, &stored.skill_files, true));
    let changed = changes.total_changed() > 0;
    if inspection.current && !changed {
        return Ok(summary(changes, false, &stored));
    }
    let corpus = load_discovered_memory_corpus(discovery);
    let graph = resolve_memory_graph(&corpus);
    let index = database::publish(&corpus, &graph, database_path)?;
    Ok(rebuilt_summary(changes, changed, &index))
}

impl ChangeCounts {
    fn add(&mut self, other: Self) {
        self.added += other.added;
        self.changed += other.changed;
        self.moved += other.moved;
        self.removed += other.removed;
        self.unchanged += other.unchanged;
    }

    fn total_changed(&self) -> usize {
        self.added + self.changed + self.moved + self.removed
    }
}

fn inspect(database_path: &Path) -> DatabaseInspection {
    if !database_path.is_file() {
        return DatabaseInspection {
            snapshot: None,
            current: false,
        };
    }
    let Ok(config) = Config::default().access_mode(AccessMode::ReadOnly) else {
        return DatabaseInspection {
            snapshot: None,
            current: false,
        };
    };
    let Ok(connection) = Connection::open_with_flags(database_path, config) else {
        return DatabaseInspection {
            snapshot: None,
            current: false,
        };
    };
    let versions = connection.query_row(
        "SELECT schema_version, parser_contract_version FROM meta",
        [],
        |row| Ok((row.get::<_, i64>(0)?, row.get::<_, i64>(1)?)),
    );
    let snapshot = read_snapshot(&connection).ok();
    let relations_valid = relations_are_valid(&connection);
    let current = matches!(
        versions,
        Ok((schema, parser))
            if schema == i64::from(constants::SCHEMA_VERSION)
                && parser == i64::from(constants::PARSER_CONTRACT_VERSION)
                && snapshot.is_some()
                && relations_valid
    );
    let _close_result = connection.close();
    DatabaseInspection { snapshot, current }
}

fn relations_are_valid(connection: &Connection) -> bool {
    for relation in schema_metadata::relations() {
        let sql = format!("SELECT * FROM {} LIMIT 0", relation.name);
        if connection.prepare(&sql).is_err() {
            return false;
        }
    }
    true
}

fn read_snapshot(connection: &Connection) -> Result<StoredIndex, duckdb::Error> {
    Ok(StoredIndex {
        documents: read_documents(connection)?,
        skill_files: read_skill_files(connection)?,
        document_count: count(connection, "documents")?,
        section_count: count(connection, "sections")?,
        link_count: count(connection, "links")?,
    })
}

fn read_documents(connection: &Connection) -> Result<Vec<SourceFact>, duckdb::Error> {
    let mut statement = connection.prepare(
        "SELECT identity, repository_relative_path, content_sha256 FROM documents ORDER BY identity, repository_relative_path",
    )?;
    statement
        .query_map([], |row| {
            let identity = row.get::<_, String>(0)?;
            Ok(SourceFact {
                key: identity.clone(),
                owner: identity,
                path: row.get(1)?,
                content_sha256: row.get(2)?,
            })
        })?
        .collect()
}

fn read_skill_files(connection: &Connection) -> Result<Vec<SourceFact>, duckdb::Error> {
    let mut statement = connection.prepare(
        "SELECT skill_identity, bundle_relative_path, repository_relative_path, content_sha256 FROM skill_files ORDER BY skill_identity, bundle_relative_path, repository_relative_path",
    )?;
    statement
        .query_map([], |row| {
            let owner = row.get::<_, String>(0)?;
            let bundle_relative_path = row.get::<_, String>(1)?;
            Ok(SourceFact {
                key: format!("{owner}\u{1f}{bundle_relative_path}"),
                owner,
                path: row.get(2)?,
                content_sha256: row.get(3)?,
            })
        })?
        .collect()
}

fn count(connection: &Connection, relation: &str) -> Result<usize, duckdb::Error> {
    let sql = format!("SELECT count(*) FROM {relation}");
    connection
        .query_row(&sql, [], |row| row.get::<_, i64>(0))
        .map(|value| value as usize)
}

fn document_facts(discovery: &DiscoveryResult) -> Vec<SourceFact> {
    discovery
        .documents
        .iter()
        .map(|document| SourceFact {
            key: document.identity.0.clone(),
            owner: document.identity.0.clone(),
            path: document.canonical_path.repository_relative.clone(),
            content_sha256: document.metadata.content_sha256.clone(),
        })
        .collect()
}

fn skill_file_facts(discovery: &DiscoveryResult) -> Vec<SourceFact> {
    discovery
        .skill_files
        .iter()
        .map(|file| SourceFact {
            key: format!(
                "{}\u{1f}{}",
                file.skill_identity.0, file.bundle_relative_path
            ),
            owner: file.skill_identity.0.clone(),
            path: file.canonical_path.repository_relative.clone(),
            content_sha256: file.metadata.content_sha256.clone(),
        })
        .collect()
}

fn classify(current: &[SourceFact], stored: &[SourceFact], match_moved_hash: bool) -> ChangeCounts {
    let mut counts = ChangeCounts::default();
    let mut remaining: BTreeMap<String, SourceFact> = stored
        .iter()
        .cloned()
        .map(|fact| (fact.key.clone(), fact))
        .collect();
    let mut additions = Vec::new();
    for fact in current {
        match remaining.remove(&fact.key) {
            Some(previous) if previous.content_sha256 != fact.content_sha256 => counts.changed += 1,
            Some(previous) if previous.path != fact.path => counts.moved += 1,
            Some(_) => counts.unchanged += 1,
            None => additions.push(fact),
        }
    }
    if match_moved_hash {
        classify_moved_additions(&mut counts, additions, &mut remaining);
    } else {
        counts.added += additions.len();
    }
    counts.removed += remaining.len();
    counts
}

fn classify_moved_additions(
    counts: &mut ChangeCounts,
    additions: Vec<&SourceFact>,
    remaining: &mut BTreeMap<String, SourceFact>,
) {
    for fact in additions {
        let moved_key = remaining
            .iter()
            .find(|(_, previous)| {
                previous.owner == fact.owner && previous.content_sha256 == fact.content_sha256
            })
            .map(|(key, _)| key.clone());
        if let Some(key) = moved_key {
            remaining.remove(&key);
            counts.moved += 1;
        } else {
            counts.added += 1;
        }
    }
}

fn summary(counts: ChangeCounts, rebuilt: bool, index: &StoredIndex) -> SyncSummary {
    SyncSummary {
        added_count: counts.added,
        changed_count: counts.changed,
        moved_count: counts.moved,
        removed_count: counts.removed,
        unchanged_count: counts.unchanged,
        rebuilt,
        changed: counts.total_changed() > 0,
        document_count: index.document_count,
        section_count: index.section_count,
        link_count: index.link_count,
    }
}

fn rebuilt_summary(counts: ChangeCounts, changed: bool, index: &IndexSummary) -> SyncSummary {
    SyncSummary {
        added_count: counts.added,
        changed_count: counts.changed,
        moved_count: counts.moved,
        removed_count: counts.removed,
        unchanged_count: counts.unchanged,
        rebuilt: true,
        changed,
        document_count: index.document_count,
        section_count: index.section_count,
        link_count: index.link_count,
    }
}
