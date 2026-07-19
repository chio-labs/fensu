//! Test-case types for CPython-shaped traversal tests.

pub(crate) struct EnumerateNodesTestCase {
    pub(crate) description: &'static str,
    pub(crate) source: &'static str,
    pub(crate) expected_kinds: &'static [&'static str],
    pub(crate) expected_first_span: Option<(u32, u32, u32, u32)>,
}

pub(crate) struct RuleAuthoringRowsTestCase {
    pub(crate) description: &'static str,
    pub(crate) class_source: &'static str,
    pub(crate) assignment_source: &'static str,
    pub(crate) call_source: &'static str,
    pub(crate) edge_source: &'static str,
    pub(crate) comparison_source: &'static str,
    pub(crate) mutation_source: &'static str,
    pub(crate) expected_class_names: &'static [&'static str],
    pub(crate) expected_base_name: &'static str,
    pub(crate) expected_method_names: &'static [&'static str],
    pub(crate) expected_target_names: &'static [&'static str],
    pub(crate) expected_assignment_reference: &'static str,
    pub(crate) expected_call_names: &'static [Option<&'static str>],
    pub(crate) expected_function_chain: &'static [&'static str],
    pub(crate) expected_literal_position: usize,
    pub(crate) expected_literal_source: &'static str,
    pub(crate) expected_bytes: &'static [u8],
    pub(crate) expected_integer: &'static str,
    pub(crate) expected_edge_callers: &'static [&'static str],
    pub(crate) expected_comparison_operand_count: usize,
    pub(crate) expected_reference_receivers: &'static [Option<&'static str>],
    pub(crate) expected_reference_parts: &'static [&'static [&'static str]],
    pub(crate) expected_mutation_lines: &'static [u32],
    pub(crate) expected_mutation_kinds: &'static [&'static str],
    pub(crate) expected_first_only_count: usize,
}

pub(crate) struct MappingRowsTestCase {
    pub(crate) description: &'static str,
    pub(crate) source: &'static str,
    pub(crate) expected_declaration_function_count: usize,
    pub(crate) expected_class_name: &'static str,
    pub(crate) expected_annotation_import_count: usize,
    pub(crate) expected_parameter_name: &'static str,
    pub(crate) expected_binding_name: Option<&'static str>,
    pub(crate) expected_calls: &'static [&'static str],
}
