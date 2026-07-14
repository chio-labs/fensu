//! Test-case types for CPython-shaped traversal tests.

pub(crate) struct EnumerateNodesTestCase {
    pub(crate) description: &'static str,
    pub(crate) source: &'static str,
    pub(crate) expected_kinds: &'static [&'static str],
    pub(crate) expected_first_span: Option<(u32, u32, u32, u32)>,
}
