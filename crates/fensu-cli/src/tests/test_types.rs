pub(crate) struct RenderColorTestCase {
    pub(crate) description: &'static str,
    pub(crate) source: &'static str,
    pub(crate) line: u32,
    pub(crate) column: u32,
    pub(crate) expected_output: &'static str,
}

pub(crate) struct PathMatchTestCase {
    pub(crate) description: &'static str,
    pub(crate) path: &'static str,
    pub(crate) pattern: &'static str,
    pub(crate) expected_matches: bool,
}

pub(crate) struct CoreRuleRenderingTestCase {
    pub(crate) description: &'static str,
    pub(crate) expected_core_count: usize,
    pub(crate) expected_labels: &'static [&'static str],
}
