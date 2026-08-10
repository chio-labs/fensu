//! Test-case models for TypeScript parser compatibility tests.

use fensu_typescript::{ModelKind, SourceKind};

pub(crate) struct ContractTestCase {
    pub(crate) description: &'static str,
    pub(crate) expected_parser_contract: &'static str,
    pub(crate) expected_cache_contract: &'static str,
    pub(crate) expected_cli_contract_fragment: &'static str,
}

pub(crate) struct DiagnosticTestCase {
    pub(crate) description: &'static str,
    pub(crate) source: &'static [u8],
    pub(crate) source_kind: SourceKind,
    pub(crate) expected_message: Option<&'static str>,
    pub(crate) expected_line: usize,
    pub(crate) expected_column: usize,
    pub(crate) expected_start: usize,
}

pub(crate) struct BindingPositionTestCase {
    pub(crate) description: &'static str,
    pub(crate) source: &'static str,
    pub(crate) binding_name: &'static str,
    pub(crate) expected_line: usize,
    pub(crate) expected_column: usize,
    pub(crate) expected_text: &'static [u8],
}

pub(crate) struct ParseSuccessTestCase {
    pub(crate) description: &'static str,
    pub(crate) source: &'static [u8],
    pub(crate) source_kind: SourceKind,
    pub(crate) expected_function_count: usize,
    pub(crate) expected_exported: bool,
}

pub(crate) struct LocalMatrixTestCase {
    pub(crate) description: &'static str,
    pub(crate) source: &'static str,
    pub(crate) expected_failures: &'static [(&'static str, usize, usize)],
    pub(crate) expected_binding_count: usize,
}

pub(crate) struct ModelMatrixTestCase {
    pub(crate) description: &'static str,
    pub(crate) source: &'static str,
    pub(crate) expected_models: &'static [(&'static str, ModelKind, bool, bool)],
}

pub(crate) struct ClassMatrixTestCase {
    pub(crate) description: &'static str,
    pub(crate) source: &'static str,
    pub(crate) expected_classes: &'static [(&'static str, bool, usize)],
}

pub(crate) struct ImportMatrixTestCase {
    pub(crate) description: &'static str,
    pub(crate) source: &'static str,
    pub(crate) expected_binding_count: usize,
    pub(crate) expected_imports: &'static [(&'static str, usize, bool, bool)],
}

pub(crate) type FunctionExpectation<'a> = (
    &'a str,
    bool,
    usize,
    bool,
    Option<&'a str>,
    usize,
    usize,
    usize,
);

pub(crate) struct FunctionMatrixTestCase {
    pub(crate) description: &'static str,
    pub(crate) source: &'static str,
    pub(crate) expected_functions: &'static [FunctionExpectation<'static>],
}

pub(crate) struct FunctionNameTestCase {
    pub(crate) description: &'static str,
    pub(crate) source: &'static str,
    pub(crate) expected_names: &'static [&'static str],
}

pub(crate) struct TopLevelBindingTestCase {
    pub(crate) description: &'static str,
    pub(crate) source: &'static str,
    pub(crate) expected_bindings: &'static [(&'static str, Option<&'static str>)],
}

pub(crate) struct PolicyFactsTestCase {
    pub(crate) description: &'static str,
    pub(crate) source: &'static str,
    pub(crate) expected_public_exports: usize,
    pub(crate) expected_runtime_declarations: usize,
    pub(crate) expected_top_level_functions: usize,
    pub(crate) expected_re_exports: usize,
    pub(crate) expected_top_level_calls: usize,
    pub(crate) expected_call_name: &'static str,
    pub(crate) expected_error_class: bool,
}

pub(crate) struct ParameterizedTestFactTestCase {
    pub(crate) description: &'static str,
    pub(crate) source: &'static str,
    pub(crate) expected_count: usize,
    pub(crate) expected_callback_name: &'static str,
    pub(crate) expected_valid_contract: bool,
}

pub(crate) struct ContractFactsTestCase {
    pub(crate) description: &'static str,
    pub(crate) source: &'static str,
    pub(crate) expected_json_states: &'static [(bool, bool)],
    pub(crate) expected_test_names: &'static [&'static str],
    pub(crate) expected_public_any: usize,
}

pub(crate) struct WebPolicyFactsTestCase {
    pub(crate) description: &'static str,
    pub(crate) source: &'static str,
    pub(crate) expected_endpoints: &'static [(&'static str, bool)],
    pub(crate) expected_dynamic_segments: &'static [&'static str],
    pub(crate) expected_export_owners: &'static [(&'static str, &'static str)],
    pub(crate) expected_cleanup_function: &'static str,
    pub(crate) expected_cleanup_target: &'static str,
    pub(crate) expected_return_function: &'static str,
    pub(crate) expected_returned_member: &'static str,
}
