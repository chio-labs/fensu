//! Canonical repository setup and DuckDB publication assertions.

use std::fs;
use std::path::{Path, PathBuf};
use std::sync::atomic::{AtomicUsize, Ordering};

use duckdb::Connection;
use strata_memory::engine::main::rebuild_memory_index::rebuild_memory_index;

use crate::test_types::{FixtureFile, MemoryPublicationTestCase};

static REPOSITORY_COUNTER: AtomicUsize = AtomicUsize::new(0);

pub(crate) fn run_case(test_case: &MemoryPublicationTestCase) {
    let root = write_repository(test_case.files);
    let database_path = root.join("generated/index/memory.duckdb");
    let first_summary = rebuild_memory_index(&root, &database_path).expect("first index rebuild");
    let existing = Connection::open(&database_path).expect("published database opens");
    existing
        .execute_batch("CREATE TABLE replacement_sentinel(value INTEGER);")
        .expect("sentinel table is writable");
    existing.close().expect("sentinel database closes");
    let summary = rebuild_memory_index(&root, &database_path).expect("replacement index rebuild");
    let connection = Connection::open(&database_path).expect("replacement database opens");
    let schema_qualified_document_count: i64 = connection
        .query_row("SELECT count(*) FROM memory.documents", [], |row| {
            row.get(0)
        })
        .expect("memory schema is directly queryable");
    assert_eq!(
        schema_qualified_document_count, test_case.expected_summary_counts[0] as i64,
        "{}: schema-qualified table access",
        test_case.description
    );
    assert_eq!(
        summary, first_summary,
        "{}: repeated rebuild summary",
        test_case.description
    );
    assert_eq!(
        summary_counts(&summary),
        test_case.expected_summary_counts,
        "{}: summary counts",
        test_case.description
    );
    assert_eq!(
        schema_versions(&connection),
        test_case.expected_schema_versions,
        "{}: schema versions",
        test_case.description
    );
    assert_eq!(
        table_names(&connection),
        test_case.expected_table_names,
        "{}: stored tables",
        test_case.description
    );
    assert_eq!(
        table_counts(&connection, test_case.expected_table_names),
        test_case.expected_table_counts,
        "{}: stored table counts",
        test_case.description
    );
    assert_eq!(
        view_names(&connection),
        test_case.expected_view_names,
        "{}: convenience views",
        test_case.description
    );
    assert_eq!(
        view_counts(&connection, test_case.expected_view_names),
        test_case.expected_view_counts,
        "{}: convenience view counts",
        test_case.description
    );
    assert_eq!(
        invalid_document(&connection),
        (
            test_case.expected_invalid_row.0.to_owned(),
            test_case.expected_invalid_row.1,
            test_case.expected_invalid_row.2,
            test_case.expected_invalid_row.3,
            test_case.expected_invalid_row.4,
        ),
        "{}: invalid document retention",
        test_case.description
    );
    assert_eq!(
        preamble_section(&connection),
        test_case.expected_preamble_row,
        "{}: synthetic preamble",
        test_case.description
    );
    assert_eq!(
        checkbox(&connection),
        (
            test_case.expected_checkbox_row.0.to_owned(),
            test_case.expected_checkbox_row.1.to_owned(),
            test_case.expected_checkbox_row.2,
            test_case.expected_checkbox_row.3.to_owned(),
            test_case.expected_checkbox_row.4.to_owned(),
            test_case.expected_checkbox_row.5.to_owned(),
        ),
        "{}: checkbox normalization",
        test_case.description
    );
    assert_eq!(
        relationship(&connection),
        (
            test_case.expected_relationship_row.0.to_owned(),
            test_case.expected_relationship_row.1.to_owned(),
            test_case.expected_relationship_row.2,
            test_case.expected_relationship_row.3,
        ),
        "{}: relationship publication",
        test_case.description
    );
    assert_eq!(
        external_status(&connection),
        test_case.expected_external_status,
        "{}: external link status",
        test_case.description
    );
    assert_eq!(
        tags(&connection),
        test_case
            .expected_tag_rows
            .iter()
            .map(|(name, section)| ((*name).to_owned(), *section))
            .collect::<Vec<(String, i64)>>(),
        "{}: tag section ownership",
        test_case.description
    );
    assert_eq!(
        phase(&connection),
        (
            test_case.expected_phase_row.0.to_owned(),
            test_case.expected_phase_row.1.to_owned(),
            test_case.expected_phase_row.2.to_owned(),
        ),
        "{}: task phase view",
        test_case.description
    );
    assert_eq!(
        skill_file(&connection),
        test_case.expected_skill_file_row,
        "{}: skill file eligibility",
        test_case.description
    );
    let sentinel_count: i64 = connection
        .query_row(
            "SELECT count(*) FROM information_schema.tables WHERE table_name = 'replacement_sentinel'",
            [],
            |row| row.get(0),
        )
        .expect("sentinel lookup succeeds");
    assert_eq!(
        sentinel_count, 0,
        "{}: existing database replacement",
        test_case.description
    );
    connection.close().expect("replacement database closes");
    assert_eq!(
        directory_files(database_path.parent().expect("database parent")),
        test_case.expected_database_files,
        "{}: temporary files are removed",
        test_case.description
    );
    fs::remove_dir_all(root).expect("temporary repository is removable");
}

pub(crate) fn write_repository(files: &[FixtureFile]) -> PathBuf {
    let sequence = REPOSITORY_COUNTER.fetch_add(1, Ordering::SeqCst);
    let root = std::env::temp_dir().join(format!(
        "strata-memory-engine-{}-{sequence}",
        std::process::id()
    ));
    let _ = fs::remove_dir_all(&root);
    fs::create_dir_all(&root).expect("temporary repository root is writable");
    for file in files {
        let path = root.join(file.path);
        fs::create_dir_all(path.parent().expect("fixture file parent"))
            .expect("fixture directory is writable");
        fs::write(path, file.contents).expect("fixture file is writable");
    }
    root
}

pub(crate) fn write_query_database() -> (PathBuf, PathBuf) {
    let root = write_repository(&[]);
    let database_path = root.join("memory.duckdb");
    let connection = Connection::open(&database_path).expect("query database opens");
    connection
        .execute_batch("CREATE TABLE sentinel(value INTEGER); INSERT INTO sentinel VALUES (7);")
        .expect("query database fixture is writable");
    connection.close().expect("query database fixture closes");
    (root, database_path)
}

pub(crate) fn sentinel_count(database_path: &Path) -> i64 {
    let connection = Connection::open(database_path).expect("query database reopens");
    let count = connection
        .query_row("SELECT count(*) FROM sentinel", [], |row| row.get(0))
        .expect("sentinel count is queryable");
    connection.close().expect("query database closes");
    count
}

pub(crate) fn tagged_query_value(
    kind: &str,
    mut fields: Vec<(String, strata_memory::engine::models::MemoryQueryValue)>,
) -> strata_memory::engine::models::MemoryQueryValue {
    fields.insert(
        0,
        (
            "$type".to_owned(),
            strata_memory::engine::models::MemoryQueryValue::String(kind.to_owned()),
        ),
    );
    strata_memory::engine::models::MemoryQueryValue::Object(fields)
}

fn summary_counts(summary: &strata_memory::engine::models::IndexSummary) -> [usize; 9] {
    [
        summary.document_count,
        summary.section_count,
        summary.list_item_count,
        summary.link_count,
        summary.tag_count,
        summary.skill_file_count,
        summary.source_diagnostic_count,
        summary.corpus_diagnostic_count,
        summary.graph_diagnostic_count,
    ]
}

fn schema_versions(connection: &Connection) -> (i32, i32) {
    connection
        .query_row(
            "SELECT schema_version, parser_contract_version FROM meta",
            [],
            |row| Ok((row.get(0)?, row.get(1)?)),
        )
        .expect("schema version row exists")
}

fn table_names(connection: &Connection) -> Vec<String> {
    query_names(
        connection,
        "SELECT table_name FROM information_schema.tables WHERE table_schema = 'main' AND table_type = 'BASE TABLE' ORDER BY table_name",
    )
}

fn view_names(connection: &Connection) -> Vec<String> {
    query_names(
        connection,
        "SELECT table_name FROM information_schema.tables WHERE table_schema = 'main' AND table_type = 'VIEW' ORDER BY table_name",
    )
}

fn query_names(connection: &Connection, sql: &str) -> Vec<String> {
    let mut statement = connection.prepare(sql).expect("name query prepares");
    statement
        .query_map([], |row| row.get(0))
        .expect("name query executes")
        .collect::<Result<Vec<String>, _>>()
        .expect("name rows decode")
}

fn table_counts(connection: &Connection, names: &[&str]) -> Vec<i64> {
    object_counts(connection, names)
}

fn view_counts(connection: &Connection, names: &[&str]) -> Vec<i64> {
    object_counts(connection, names)
}

fn object_counts(connection: &Connection, names: &[&str]) -> Vec<i64> {
    let mut counts = Vec::new();
    for name in names {
        let sql = format!("SELECT count(*) FROM {name}");
        counts.push(
            connection
                .query_row(&sql, [], |row| row.get(0))
                .expect("object count query succeeds"),
        );
    }
    counts
}

fn invalid_document(connection: &Connection) -> (String, i64, bool, bool, bool) {
    connection
        .query_row(
            "SELECT parse_status, diagnostic_count, raw_markdown IS NULL, plain_text IS NULL, title IS NULL FROM documents WHERE slug = 'invalid-note'",
            [],
            |row| Ok((row.get(0)?, row.get(1)?, row.get(2)?, row.get(3)?, row.get(4)?)),
        )
        .expect("invalid document row exists")
}

fn preamble_section(connection: &Connection) -> (i64, bool, i64) {
    connection
        .query_row(
            "SELECT ordinal, heading_ordinal IS NULL, start_line FROM sections WHERE document_identity = 'task:20260717T120000_000000Z' AND ordinal = 0",
            [],
            |row| Ok((row.get(0)?, row.get(1)?, row.get(2)?)),
        )
        .expect("preamble section exists")
}

fn checkbox(connection: &Connection) -> (String, String, i64, String, String, String) {
    connection
        .query_row(
            "SELECT checkbox_raw, checkbox_state, section_ordinal, kind, heading_path, raw_markdown FROM task_checkboxes",
            [],
            |row| {
                Ok((
                    row.get(0)?,
                    row.get(1)?,
                    row.get(2)?,
                    row.get(3)?,
                    row.get(4)?,
                    row.get(5)?,
                ))
            },
        )
        .expect("task checkbox exists")
}

fn relationship(connection: &Connection) -> (String, String, bool, i64) {
    connection
        .query_row(
            "SELECT relationship_kind, resolution_status, explicit, section_ordinal FROM relationships",
            [],
            |row| Ok((row.get(0)?, row.get(1)?, row.get(2)?, row.get(3)?)),
        )
        .expect("relationship exists")
}

fn external_status(connection: &Connection) -> String {
    connection
        .query_row(
            "SELECT resolution_status FROM links WHERE syntax_kind = 'external-url'",
            [],
            |row| row.get(0),
        )
        .expect("external link exists")
}

fn tags(connection: &Connection) -> Vec<(String, i64)> {
    let mut statement = connection
        .prepare("SELECT name, section_ordinal FROM tags ORDER BY name")
        .expect("tag query prepares");
    statement
        .query_map([], |row| Ok((row.get(0)?, row.get(1)?)))
        .expect("tag query executes")
        .collect::<Result<Vec<(String, i64)>, _>>()
        .expect("tag rows decode")
}

fn phase(connection: &Connection) -> (String, String, String) {
    connection
        .query_row(
            "SELECT semantic_kind, phase_key, phase_title FROM task_phases",
            [],
            |row| Ok((row.get(0)?, row.get(1)?, row.get(2)?)),
        )
        .expect("task phase exists")
}

fn skill_file(connection: &Connection) -> (bool, bool) {
    connection
        .query_row(
            "SELECT archived, install_eligible FROM skill_files",
            [],
            |row| Ok((row.get(0)?, row.get(1)?)),
        )
        .expect("skill file exists")
}

fn directory_files(path: &Path) -> Vec<String> {
    let mut names: Vec<String> = fs::read_dir(path)
        .expect("database directory is readable")
        .map(|entry| {
            entry
                .expect("database directory entry is readable")
                .file_name()
                .to_string_lossy()
                .into_owned()
        })
        .collect();
    names.sort();
    names
}
