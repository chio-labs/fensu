pub(crate) struct RenderColorTestCase {
    pub(crate) description: &'static str,
    pub(crate) source: &'static str,
    pub(crate) line: u32,
    pub(crate) column: u32,
    pub(crate) expected_output: &'static str,
}
