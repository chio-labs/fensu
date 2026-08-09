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
    pub(crate) expected_models: &'static [(&'static str, ModelKind, bool)],
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
