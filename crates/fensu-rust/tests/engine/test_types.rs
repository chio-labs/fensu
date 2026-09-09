pub(crate) struct EngineTestCase {
    pub(crate) description: &'static str,
    pub(crate) expected_cache_contract: &'static str,
    pub(crate) expected_diagnostics: bool,
    pub(crate) expected_lock_created: bool,
    pub(crate) expected_parser_contract: &'static str,
}
