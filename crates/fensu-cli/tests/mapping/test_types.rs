//! Mapping command test case models.

pub(crate) struct ConfiguredPackageMappingTestCase {
    pub(crate) description: &'static str,
    pub(crate) package_name: &'static str,
    pub(crate) expected_function_path: &'static str,
}

pub(crate) struct ConfigTargetMappingTestCase {
    pub(crate) description: &'static str,
    pub(crate) arguments: &'static [&'static str],
    pub(crate) expected_exit_code: i32,
    pub(crate) expected_stdout: &'static str,
    pub(crate) expected_stderr: &'static str,
}
