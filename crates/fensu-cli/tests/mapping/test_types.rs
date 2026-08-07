//! Mapping command test case models.

pub(crate) struct ConfiguredPackageMappingTestCase {
    pub(crate) description: &'static str,
    pub(crate) package_name: &'static str,
    pub(crate) expected_function_path: &'static str,
}
