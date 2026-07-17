//! Test-case types for native memory tuple conversion.

pub(crate) struct SummaryConversionTestCase {
    pub(crate) description: &'static str,
    pub(crate) expected_sync: (
        usize,
        usize,
        usize,
        usize,
        usize,
        bool,
        bool,
        usize,
        usize,
        usize,
    ),
    pub(crate) expected_overview: (
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

pub(crate) struct SchemaConversionTestCase {
    pub(crate) description: &'static str,
    pub(crate) expected_versions: (u32, u32),
    pub(crate) expected_relation_count: usize,
    pub(crate) expected_first_relation: &'static str,
    pub(crate) expected_focused_relation: &'static str,
    pub(crate) expected_focused_kind: &'static str,
    pub(crate) expected_first_column: &'static str,
    pub(crate) expected_first_type: &'static str,
}
