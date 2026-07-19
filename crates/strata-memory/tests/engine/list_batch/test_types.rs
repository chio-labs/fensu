//! Test case types for SQLite list-batch transaction behavior.

pub(crate) struct MemoryListBatchFailureTestCase {
    pub(crate) description: &'static str,
    pub(crate) expected_error_fragment: &'static str,
    pub(crate) expected_row_count: i64,
}
