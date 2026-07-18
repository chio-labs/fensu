//! Version numbers, insert statements, and the SQLite memory SQL contract.

pub(crate) const MAX_QUERY_SQL_BYTES: usize = 64 * 1024;
pub(crate) const MIN_QUERY_LIMIT: usize = 1;
pub(crate) const MAX_QUERY_LIMIT: usize = 1000;
pub(crate) const MAX_QUERY_COLUMNS: usize = 256;
pub(crate) const MAX_QUERY_RESULT_BYTES: usize = 8 * 1024 * 1024;
pub(crate) const QUERY_NULL_TYPE: &str = "Null";
pub(crate) const PUBLICATION_DOCUMENT_CHUNK: usize = 512;
pub(crate) const LIST_KIND_UNORDERED_CODE: u8 = 0;
pub(crate) const LIST_KIND_ORDERED_CODE: u8 = 1;
pub(crate) const SCHEMA_VERSION: u32 = 3;
pub(crate) const PARSER_CONTRACT_VERSION: u32 = 1;
pub(crate) const ARCHIVE_STATE_ACTIVE: &str = "active";
pub(crate) const ARCHIVE_STATE_ARCHIVED: &str = "archived";
pub(crate) const RESOLUTION_STATUS_RESOLVED: &str = "resolved";

pub(crate) const MEMORY_SCHEMA_SQL: &str = r#"
CREATE TABLE meta (
    schema_version INTEGER PRIMARY KEY,
    parser_contract_version INTEGER NOT NULL
);

CREATE TABLE _document_keys (
    document_key UBIGINT NOT NULL,
    identity VARCHAR NOT NULL
);

CREATE TABLE documents (
    identity VARCHAR PRIMARY KEY,
    artifact_kind VARCHAR NOT NULL,
    task_category VARCHAR,
    lifecycle VARCHAR,
    archive_state VARCHAR NOT NULL,
    repository_relative_path VARCHAR NOT NULL UNIQUE,
    filesystem_path VARCHAR NOT NULL,
    basename VARCHAR NOT NULL,
    slug VARCHAR NOT NULL,
    creation_timestamp VARCHAR,
    content_sha256 VARCHAR NOT NULL,
    byte_size UBIGINT NOT NULL,
    modified_at_ns HUGEINT NOT NULL,
    changed_at_ns HUGEINT,
    git_tracking VARCHAR NOT NULL,
    parse_status VARCHAR NOT NULL,
    diagnostic_count UBIGINT NOT NULL,
    raw_markdown VARCHAR,
    plain_text VARCHAR,
    title VARCHAR,
    CHECK (parse_status IN ('valid', 'invalid'))
);

CREATE TABLE sections (
    document_identity VARCHAR NOT NULL,
    ordinal UBIGINT NOT NULL,
    heading_ordinal UBIGINT,
    heading_level UTINYINT,
    heading_text VARCHAR,
    heading_slug VARCHAR,
    heading_path VARCHAR,
    semantic_kind VARCHAR,
    phase_key VARCHAR,
    phase_title VARCHAR,
    raw_markdown VARCHAR NOT NULL,
    plain_text VARCHAR NOT NULL,
    start_byte UBIGINT NOT NULL,
    end_byte UBIGINT NOT NULL,
    start_line UBIGINT NOT NULL,
    end_line UBIGINT NOT NULL,
    PRIMARY KEY (document_identity, ordinal),
    FOREIGN KEY (document_identity) REFERENCES documents(identity)
);

CREATE TABLE _list_items (
    document_key UBIGINT NOT NULL,
    ordinal UBIGINT NOT NULL,
    section_ordinal UBIGINT,
    parent_ordinal UBIGINT,
    kind VARCHAR NOT NULL,
    nesting_depth UBIGINT NOT NULL,
    ordered_number UBIGINT,
    raw_end_byte UBIGINT NOT NULL,
    plain_text VARCHAR NOT NULL,
    source_line UBIGINT NOT NULL,
    start_byte UBIGINT NOT NULL,
    end_byte UBIGINT NOT NULL,
    start_line UBIGINT NOT NULL,
    end_line UBIGINT NOT NULL,
    checkbox_raw VARCHAR,
    checkbox_state VARCHAR,
    leading_key VARCHAR,
    relationship_kind VARCHAR
);

CREATE TABLE links (
    document_identity VARCHAR NOT NULL,
    ordinal UBIGINT NOT NULL,
    section_ordinal UBIGINT,
    list_item_ordinal UBIGINT,
    syntax_kind VARCHAR NOT NULL,
    target VARCHAR NOT NULL,
    alias VARCHAR,
    display_text VARCHAR,
    heading_fragment VARCHAR,
    resolved_document_identity VARCHAR,
    resolved_section_ordinal UBIGINT,
    resolution_status VARCHAR NOT NULL,
    relationship_kind VARCHAR,
    explicit BOOLEAN NOT NULL,
    raw_source VARCHAR NOT NULL,
    source_line UBIGINT NOT NULL,
    start_byte UBIGINT NOT NULL,
    end_byte UBIGINT NOT NULL,
    start_line UBIGINT NOT NULL,
    end_line UBIGINT NOT NULL,
    PRIMARY KEY (document_identity, ordinal),
    FOREIGN KEY (document_identity) REFERENCES documents(identity),
    FOREIGN KEY (resolved_document_identity) REFERENCES documents(identity)
);

CREATE TABLE tags (
    document_identity VARCHAR NOT NULL,
    ordinal UBIGINT NOT NULL,
    section_ordinal UBIGINT,
    name VARCHAR NOT NULL,
    raw_source VARCHAR NOT NULL,
    source_line UBIGINT NOT NULL,
    start_byte UBIGINT NOT NULL,
    end_byte UBIGINT NOT NULL,
    start_line UBIGINT NOT NULL,
    end_line UBIGINT NOT NULL,
    PRIMARY KEY (document_identity, ordinal),
    FOREIGN KEY (document_identity) REFERENCES documents(identity)
);

CREATE TABLE skill_files (
    skill_identity VARCHAR NOT NULL,
    repository_relative_path VARCHAR NOT NULL PRIMARY KEY,
    filesystem_path VARCHAR NOT NULL,
    bundle_relative_path VARCHAR NOT NULL,
    content_sha256 VARCHAR NOT NULL,
    byte_size UBIGINT NOT NULL,
    modified_at_ns HUGEINT NOT NULL,
    changed_at_ns HUGEINT,
    git_tracking VARCHAR NOT NULL,
    archived BOOLEAN NOT NULL,
    install_eligible BOOLEAN NOT NULL,
    FOREIGN KEY (skill_identity) REFERENCES documents(identity)
);

CREATE VIEW list_items AS
SELECT
    document.identity AS document_identity,
    item.ordinal,
    item.section_ordinal,
    item.parent_ordinal,
    CASE item.kind WHEN 1 THEN 'ordered' ELSE 'unordered' END AS kind,
    item.nesting_depth,
    item.ordered_number,
    COALESCE(section.heading_path, '') AS heading_path,
    substring(
        source.raw_markdown,
        CAST(item.start_byte + 1 AS BIGINT),
        CAST(item.raw_end_byte - item.start_byte AS BIGINT)
    ) AS raw_markdown,
    item.plain_text,
    item.source_line,
    item.start_byte,
    item.end_byte,
    item.start_line,
    item.end_line,
    item.checkbox_raw,
    item.checkbox_state,
    item.leading_key,
    item.relationship_kind
FROM _list_items AS item
JOIN _document_keys AS document
    ON document.document_key = item.document_key
JOIN documents AS source
    ON source.identity = document.identity
LEFT JOIN sections AS section
    ON section.document_identity = document.identity
    AND section.ordinal = item.section_ordinal;

INSERT INTO meta VALUES (3, 1);

CREATE VIEW current_documents AS
SELECT * FROM documents WHERE archive_state = 'active';

CREATE VIEW tasks AS
SELECT * FROM documents WHERE artifact_kind = 'task';

CREATE VIEW current_tasks AS
SELECT * FROM current_documents WHERE artifact_kind = 'task';

CREATE VIEW archived_tasks AS
SELECT * FROM tasks WHERE archive_state = 'archived';

CREATE VIEW task_phases AS
SELECT
    task.identity AS document_identity,
    task.title AS document_title,
    section.ordinal AS section_ordinal,
    section.semantic_kind,
    section.phase_key,
    section.phase_title,
    section.heading_text,
    section.heading_path,
    section.raw_markdown,
    section.plain_text,
    section.start_line,
    section.end_line
FROM current_tasks AS task
JOIN sections AS section ON section.document_identity = task.identity
WHERE section.semantic_kind IN ('phase', 'stage', 'milestone', 'checkpoint');

CREATE VIEW checkboxes AS
SELECT
    document.artifact_kind,
    document.lifecycle,
    item.*
FROM list_items AS item
JOIN current_documents AS document ON document.identity = item.document_identity
WHERE item.checkbox_state IS NOT NULL;

CREATE VIEW task_checkboxes AS
SELECT checkbox.*
FROM checkboxes AS checkbox
JOIN current_tasks AS task ON task.identity = checkbox.document_identity;

CREATE VIEW relationships AS
SELECT
    document.artifact_kind AS source_artifact_kind,
    document.title AS source_title,
    link.*
FROM links AS link
JOIN current_documents AS document ON document.identity = link.document_identity
WHERE link.relationship_kind IS NOT NULL;

CREATE VIEW task_dependencies AS
SELECT
    relationship.*,
    target.artifact_kind AS target_artifact_kind,
    target.lifecycle AS target_lifecycle,
    CASE
        WHEN relationship.resolution_status != 'resolved' THEN 'unresolved'
        WHEN target.artifact_kind != 'task' THEN 'unresolved'
        WHEN target.lifecycle = 'completed' THEN 'satisfied'
        WHEN target.lifecycle IN ('not-started', 'in-progress') THEN 'blocking'
        ELSE 'unresolved'
    END AS dependency_state
FROM relationships AS relationship
JOIN current_tasks AS task ON task.identity = relationship.document_identity
LEFT JOIN documents AS target ON target.identity = relationship.resolved_document_identity
WHERE relationship.relationship_kind = 'depends-on';

CREATE VIEW blocked_tasks AS
SELECT task.*
FROM current_tasks AS task
WHERE EXISTS (
    SELECT 1
    FROM task_dependencies AS dependency
    WHERE dependency.document_identity = task.identity
      AND dependency.dependency_state != 'satisfied'
);

CREATE VIEW notes AS
SELECT * FROM current_documents WHERE artifact_kind = 'note';

CREATE VIEW decisions AS
SELECT * FROM current_documents WHERE artifact_kind = 'decision';

CREATE VIEW skills AS
SELECT
    document.*,
    (
        SELECT count(*)
        FROM skill_files AS counted_file
        WHERE counted_file.skill_identity = document.identity
    ) AS support_file_count,
    document.parse_status = 'valid' AND NOT EXISTS (
        SELECT 1
        FROM skill_files AS ineligible_file
        WHERE ineligible_file.skill_identity = document.identity
          AND NOT ineligible_file.install_eligible
    ) AS install_eligible
FROM current_documents AS document
WHERE document.artifact_kind = 'skill';

CREATE VIEW broken_links AS
SELECT * FROM links WHERE resolution_status IN ('unresolved', 'ambiguous');

"#;
