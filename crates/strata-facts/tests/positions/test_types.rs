//! Test-case types for position conversion tests.

pub(crate) struct LocateOffsetTestCase {
    pub(crate) description: &'static str,
    pub(crate) source: &'static str,
    pub(crate) offset: usize,
    pub(crate) expected_line: u32,
    pub(crate) expected_column: u32,
}
