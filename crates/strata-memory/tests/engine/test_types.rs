//! Test-case types for memory engine behavior.

use std::time::Duration;

pub(crate) struct FixtureFile {
    pub(crate) path: &'static str,
    pub(crate) contents: &'static [u8],
}

pub(crate) struct DependencyProbeTestCase {
    pub(crate) description: &'static str,
    pub(crate) expected_version_prefix: &'static str,
}

pub(crate) struct MemoryPublicationTestCase {
    pub(crate) description: &'static str,
    pub(crate) files: &'static [FixtureFile],
    pub(crate) expected_table_names: &'static [&'static str],
    pub(crate) expected_table_counts: &'static [i64],
    pub(crate) expected_view_names: &'static [&'static str],
    pub(crate) expected_view_counts: &'static [i64],
    pub(crate) expected_summary_counts: [usize; 9],
    pub(crate) expected_schema_versions: (i32, i32),
    pub(crate) expected_invalid_row: (&'static str, i64, bool, bool, bool),
    pub(crate) expected_preamble_row: (i64, bool, i64),
    pub(crate) expected_checkbox_row: (
        &'static str,
        &'static str,
        i64,
        &'static str,
        &'static str,
        &'static str,
    ),
    pub(crate) expected_relationship_row: (&'static str, &'static str, bool, i64),
    pub(crate) expected_external_status: &'static str,
    pub(crate) expected_tag_rows: &'static [(&'static str, i64)],
    pub(crate) expected_phase_row: (&'static str, &'static str, &'static str),
    pub(crate) expected_skill_file_row: (bool, bool),
    pub(crate) expected_database_files: &'static [&'static str],
}

pub(crate) struct MemoryQueryTestCase {
    pub(crate) description: &'static str,
    pub(crate) sql: &'static str,
    pub(crate) limit: usize,
    pub(crate) expected_columns: &'static [&'static str],
    pub(crate) expected_types: &'static [&'static str],
    pub(crate) expected_row_count: usize,
    pub(crate) expected_truncated: bool,
}

pub(crate) struct InvalidMemoryQueryTestCase {
    pub(crate) description: &'static str,
    pub(crate) sql: &'static str,
    pub(crate) limit: usize,
    pub(crate) expected_error_fragment: &'static str,
}

pub(crate) struct MemoryGraphTraversalTestCase {
    pub(crate) description: &'static str,
    pub(crate) pattern: &'static str,
    pub(crate) direction: strata_memory::engine::models::MemoryGraphDirection,
    pub(crate) relationships: &'static [strata_memory::engine::models::MemoryGraphRelationship],
    pub(crate) depth: usize,
    pub(crate) max_nodes: usize,
    pub(crate) max_edges: usize,
    pub(crate) include_archived: bool,
    pub(crate) expected_selection: &'static str,
    pub(crate) expected_roots: &'static [&'static str],
    pub(crate) expected_nodes: &'static [&'static str],
    pub(crate) expected_edge_count: usize,
    pub(crate) expected_node_exhausted: bool,
    pub(crate) expected_edge_exhausted: bool,
}

pub(crate) struct InvalidMemoryGraphTestCase {
    pub(crate) description: &'static str,
    pub(crate) pattern: &'static str,
    pub(crate) depth: usize,
    pub(crate) max_nodes: usize,
    pub(crate) max_edges: usize,
    pub(crate) include_archived: bool,
    pub(crate) expected_error_fragment: &'static str,
}

pub(crate) struct MemorySummaryTestCase {
    pub(crate) description: &'static str,
    pub(crate) files: &'static [FixtureFile],
    pub(crate) expected_summary_counts: [usize; 9],
    pub(crate) expected_database_exists: bool,
}

pub(crate) struct MemorySyncTestCase {
    pub(crate) description: &'static str,
    pub(crate) files: &'static [FixtureFile],
    pub(crate) expected_initial: (usize, usize, usize, usize, usize, bool, bool),
    pub(crate) expected_unchanged: (usize, usize, usize, usize, usize, bool, bool),
    pub(crate) expected_edit: (usize, usize, bool),
    pub(crate) expected_document_move: (usize, usize),
    pub(crate) expected_support_move: (usize, usize),
    pub(crate) expected_remove: (usize, usize),
}

pub(crate) struct MemoryRecoveryTestCase {
    pub(crate) description: &'static str,
    pub(crate) files: &'static [FixtureFile],
    pub(crate) expected_incompatible: (usize, usize, bool, bool),
    pub(crate) expected_corrupt: (usize, usize, bool, bool),
    pub(crate) expected_document_count: i64,
}

pub(crate) struct MemoryConcurrentPublicationTestCase {
    pub(crate) description: &'static str,
    pub(crate) files: &'static [FixtureFile],
    pub(crate) added_file: FixtureFile,
    pub(crate) expected_reader_document_count: i64,
    pub(crate) expected_published_document_count: i64,
}

pub(crate) struct MemoryPermissionFailureTestCase {
    pub(crate) description: &'static str,
    pub(crate) files: &'static [FixtureFile],
    pub(crate) changed_contents: &'static [u8],
    pub(crate) expected_error_fragment: &'static str,
}

pub(crate) struct MemoryOverviewTestCase {
    pub(crate) description: &'static str,
    pub(crate) files: &'static [FixtureFile],
    pub(crate) expected_counts: (
        usize,
        usize,
        usize,
        usize,
        usize,
        usize,
        usize,
        usize,
        usize,
        usize,
        usize,
        usize,
    ),
}

pub(crate) struct MemoryPublicationPerformanceTestCase {
    pub(crate) description: &'static str,
    pub(crate) document_count: usize,
    pub(crate) list_items_per_document: usize,
    pub(crate) list_marker: &'static str,
    pub(crate) expected_list_item_count: usize,
    pub(crate) expected_list_item_batch_count: usize,
    pub(crate) expected_max_duration: Duration,
}

pub(crate) struct MemoryPublicationStressTestCase {
    pub(crate) description: &'static str,
    pub(crate) document_count: usize,
    pub(crate) list_items_per_document: usize,
    pub(crate) expected_document_count: usize,
    pub(crate) expected_list_item_count: usize,
    pub(crate) expected_list_item_batch_count: usize,
}

pub(crate) struct MemorySchemaTestCase {
    pub(crate) description: &'static str,
    pub(crate) expected_versions: (u32, u32),
    pub(crate) expected_relation_count: usize,
    pub(crate) expected_relation_name: &'static str,
    pub(crate) expected_focused: (&'static str, &'static str, usize),
    pub(crate) expected_first_column: (&'static str, &'static str, bool, &'static str),
}

pub(crate) struct MemoryCheckTestCase {
    pub(crate) description: &'static str,
    pub(crate) files: &'static [FixtureFile],
    pub(crate) expected_diagnostics: &'static [(&'static str, &'static str, Option<usize>)],
    pub(crate) expected_published: bool,
}

pub(crate) struct MemoryArchiveTestCase {
    pub(crate) description: &'static str,
    pub(crate) files: &'static [FixtureFile],
    pub(crate) requested_path: &'static str,
    pub(crate) confirmed: bool,
    pub(crate) expected_source_exists: bool,
    pub(crate) expected_destination: &'static str,
    pub(crate) expected_move_count: usize,
}

pub(crate) struct MemoryArchiveTaskTestCase {
    pub(crate) description: &'static str,
    pub(crate) files: &'static [FixtureFile],
    pub(crate) completed_path: &'static str,
    pub(crate) active_path: &'static str,
    pub(crate) expected_confirmation_error: &'static str,
    pub(crate) expected_lifecycle_error: &'static str,
    pub(crate) expected_move_count: usize,
}

pub(crate) struct MemoryArchiveAutomaticTestCase {
    pub(crate) description: &'static str,
    pub(crate) files: &'static [FixtureFile],
    pub(crate) archive_after_days: u64,
    pub(crate) expected_move_count: usize,
    pub(crate) expected_sync: bool,
    pub(crate) expected_database_exists: bool,
}

pub(crate) struct MemoryArchiveCtimeTestCase {
    pub(crate) description: &'static str,
    pub(crate) file: FixtureFile,
    pub(crate) archive_after_days: u64,
    pub(crate) old_mtime_days: u64,
    pub(crate) expected_move_count: usize,
}
