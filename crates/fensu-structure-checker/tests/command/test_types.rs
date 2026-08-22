//! Command test inputs and expected process results.

pub(crate) struct CommandTestCase {
    pub(crate) description: &'static str,
    pub(crate) arguments: Vec<&'static str>,
    pub(crate) expected_status: i32,
    pub(crate) expected_stdout: &'static str,
    pub(crate) expected_stderr: &'static str,
}
