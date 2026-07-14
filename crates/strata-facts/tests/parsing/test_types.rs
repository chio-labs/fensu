//! Test-case types for strict parsing tests.

pub(crate) struct ParseStrictTestCase {
    pub(crate) description: &'static str,
    pub(crate) source: &'static str,
    pub(crate) python_minor: u8,
    pub(crate) expected_valid: bool,
    pub(crate) expected_failure_line: u32,
}
