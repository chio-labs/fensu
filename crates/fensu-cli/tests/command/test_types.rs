pub(crate) struct NativeMemoryCommandTestCase {
    pub(crate) description: &'static str,
    pub(crate) expected_exit_code: i32,
    pub(crate) expected_output: &'static str,
}

pub(crate) struct InvalidMemoryArgumentsTestCase {
    pub(crate) description: &'static str,
    pub(crate) arguments: &'static [&'static str],
    pub(crate) expected_exit_code: i32,
    pub(crate) expected_error: &'static str,
}
