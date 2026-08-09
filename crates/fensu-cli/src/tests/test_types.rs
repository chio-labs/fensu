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

pub(crate) struct CacheIdentityFramingTestCase {
    pub(crate) description: &'static str,
    pub(crate) first_analyzer: &'static str,
    pub(crate) first_target: &'static str,
    pub(crate) first_root: &'static str,
    pub(crate) second_analyzer: &'static str,
    pub(crate) second_target: &'static str,
    pub(crate) second_root: &'static str,
    pub(crate) expected_equal: bool,
}

pub(crate) struct TargetRootRepresentationTestCase {
    pub(crate) description: &'static str,
    pub(crate) configured: &'static str,
    pub(crate) expected_root: &'static str,
}

pub(crate) struct MissingSuffixSymlinkTargetTestCase {
    pub(crate) description: &'static str,
    pub(crate) configured: &'static str,
    pub(crate) expected_root: &'static str,
}

pub(crate) struct EscapingSymlinkTargetTestCase {
    pub(crate) description: &'static str,
    pub(crate) configured: &'static str,
    pub(crate) expected_error: &'static str,
}

pub(crate) struct CoreRuleRenderingTestCase {
    pub(crate) description: &'static str,
    pub(crate) expected_core_count: usize,
    pub(crate) expected_labels: &'static [&'static str],
}
