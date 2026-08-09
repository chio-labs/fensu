//! Test-case models for Svelte parser compatibility tests.

pub(crate) struct ContractTestCase {
    pub(crate) description: &'static str,
    pub(crate) expected_parser_contract: &'static str,
    pub(crate) expected_cache_contract: &'static str,
    pub(crate) expected_recovery_kinds: &'static [&'static str],
    pub(crate) expected_cli_contract_fragment: &'static str,
}

pub(crate) struct TemplateSuccessTestCase {
    pub(crate) description: &'static str,
    pub(crate) source: &'static str,
    pub(crate) expected_script_count: usize,
}

pub(crate) struct ScriptContextTestCase {
    pub(crate) description: &'static str,
    pub(crate) source: &'static str,
    pub(crate) expected_context: fensu_svelte::ScriptContext,
    pub(crate) expected_function_count: usize,
}

pub(crate) struct DiagnosticTestCase {
    pub(crate) description: &'static str,
    pub(crate) source: &'static [u8],
    pub(crate) expected_message: Option<&'static str>,
    pub(crate) expected_message_prefix: Option<&'static str>,
    pub(crate) expected_line: usize,
    pub(crate) expected_column: Option<usize>,
    pub(crate) expected_start: Option<usize>,
}

pub(crate) struct DualScriptTestCase {
    pub(crate) description: &'static str,
    pub(crate) source: &'static str,
    pub(crate) expected_module_line: usize,
    pub(crate) expected_import_line: usize,
    pub(crate) expected_local_line: usize,
    pub(crate) expected_local_column: usize,
    pub(crate) expected_local_text: &'static str,
}

pub(crate) struct RuneTestCase {
    pub(crate) description: &'static str,
    pub(crate) source: &'static str,
    pub(crate) expected_runes: &'static [(&'static str, usize, usize)],
}

pub(crate) struct CompatibilityTestCase {
    pub(crate) description: &'static str,
    pub(crate) source: &'static str,
    pub(crate) expected_script_count: usize,
}

pub(crate) struct ClassPositionTestCase {
    pub(crate) description: &'static str,
    pub(crate) source: &'static str,
    pub(crate) expected_line: usize,
    pub(crate) expected_column: usize,
    pub(crate) expected_text: &'static str,
}

pub(crate) struct DuplicateScriptTestCase {
    pub(crate) description: &'static str,
    pub(crate) source: &'static [u8],
    pub(crate) expected_message: &'static str,
    pub(crate) expected_line: usize,
    pub(crate) expected_column: usize,
}
