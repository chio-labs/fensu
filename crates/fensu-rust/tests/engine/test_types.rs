pub(crate) struct EngineTestCase {
    pub(crate) description: &'static str,
    pub(crate) expected_cache_contract: &'static str,
    pub(crate) expected_diagnostics: bool,
    pub(crate) expected_lock_created: bool,
    pub(crate) expected_parser_contract: &'static str,
}

pub(crate) struct RustFactsEngineTestCase {
    pub(crate) description: &'static str,
    pub(crate) expected_schema: &'static str,
    pub(crate) expected_parser: &'static str,
    pub(crate) expected_crate: &'static str,
    pub(crate) expected_item_kind: &'static str,
    pub(crate) expected_visibility: &'static str,
    pub(crate) expected_derive: &'static str,
    pub(crate) expected_resolution: &'static str,
    pub(crate) expected_target: &'static str,
    pub(crate) expected_main_module: &'static [&'static str],
    pub(crate) expected_library_target: &'static str,
    pub(crate) expected_binary_resolution: &'static str,
    pub(crate) expected_lock_created: bool,
}
