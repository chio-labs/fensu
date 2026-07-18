//! Native rule registrations and their consumed public fact families.

pub const PARAMETER_ANNOTATION_CODE: &str = "SFA001";
pub const RETURN_ANNOTATION_CODE: &str = "SFA002";
pub const MODULE_VARIABLE_ANNOTATION_CODE: &str = "SFA101";
pub const CLASS_ATTRIBUTE_ANNOTATION_CODE: &str = "SFA102";
pub const LOCAL_VARIABLE_ANNOTATION_CODE: &str = "SFA103";
pub const SINGLE_LINE_DOCSTRINGS_CODE: &str = "SFH001";
pub const NO_STANDALONE_COMMENTS_CODE: &str = "SFH002";
pub const NO_RAW_BUILTIN_RAISE_CODE: &str = "SFH003";
pub const NO_ASSERT_IN_RUNTIME_CODE: &str = "SFH004";
pub const NO_SWALLOWED_EXCEPTION_PROBE_CODE: &str = "SFH005";
pub const NO_COMPLEX_COMPREHENSIONS_IN_TOOLING_CODE: &str = "SFH006";
pub const NO_UNNAMED_STRING_DECISIONS_CODE: &str = "SFH007";
pub const NO_MAGIC_NUMERIC_COMPARISONS_CODE: &str = "SFH008";
pub const NO_IMPORT_TIME_SIDE_EFFECTS_CODE: &str = "SFH009";
pub const TOO_MANY_STATEMENTS_CODE: &str = "SFS001";
pub const TOO_MANY_DISTINCT_CALLS_CODE: &str = "SFS002";
pub const TOO_MANY_LOCALS_CODE: &str = "SFS003";
pub const MAX_ARGUMENTS_CODE: &str = "SFS010";
pub const MAX_STATEMENTS_GLOBAL_CODE: &str = "SFS011";
pub const PARAMETER_MUTATION_IN_PHASE_HELPERS_CODE: &str = "SFS102";
pub const DEFAULT_MUTATION_RETURN_CODE: &str = "SFS110";
pub const KEYWORD_ONLY_ARGUMENTS_CODE: &str = "SFS120";
pub const NO_OUTER_STATE_MUTATION_CODE: &str = "SFS130";
pub const NO_COMPLEX_COMPREHENSIONS_CODE: &str = "SFS131";
pub const MUTABLE_RESULT_MODEL_CODE: &str = "SFS201";
pub const VALIDATOR_MUST_NOT_RETURN_CODE: &str = "SFN001";
pub const PREDICATE_MUST_RETURN_BOOL_CODE: &str = "SFN002";
pub const VALUE_NAME_MUST_RETURN_VALUE_CODE: &str = "SFN003";
pub const ITERATOR_NAME_MUST_PRODUCE_ITERATOR_CODE: &str = "SFN004";
pub const ABSOLUTE_IMPORTS_ONLY_CODE: &str = "SFL001";
pub const NO_STAR_IMPORTS_CODE: &str = "SFL002";
pub const NO_CROSS_FILE_HELPER_PRIVATE_CLASS_CODE: &str = "SFL110";
pub const PRIVATE_DEFINITION_ORDERING_CODE: &str = "SFR503";
pub const TEST_INIT_MODULE_EMPTY_CODE: &str = "SFT101";
pub const TEST_ABSOLUTE_IMPORTS_CODE: &str = "SFT102";
pub const TEST_NO_TOP_LEVEL_HELPERS_CODE: &str = "SFT103";
pub const TEST_NO_IF_IN_TESTS_CODE: &str = "SFT104";
pub const TEST_PRIVATE_CONSTANT_ORDER_CODE: &str = "SFT105";
pub const TEST_NO_COMPLEX_COMPREHENSIONS_CODE: &str = "SFT106";
pub const TEST_TYPES_DESCRIPTION_CODE: &str = "SFT201";
pub const TEST_TYPES_EXPECTED_FIELD_CODE: &str = "SFT202";
pub const TEST_LOCAL_TEST_TYPES_IMPORT_CODE: &str = "SFT203";
pub const TEST_FILE_NAME_CODE: &str = "SFT301";
pub const TEST_FUNCTION_NAME_CODE: &str = "SFT302";
pub const TEST_DATACLASS_PARAMETRIZE_CODE: &str = "SFT401";
pub const TEST_ACCEPTS_TEST_CASE_CODE: &str = "SFT402";
pub const TEST_EXPECTED_FIELD_ASSERTION_CODE: &str = "SFT404";
pub const TEST_PARAMETRIZE_ARGUMENTS_CODE: &str = "SFT405";
pub const TEST_PARAMETRIZE_TEST_CASE_CODE: &str = "SFT406";
pub const TEST_PARAMETRIZE_IDS_CODE: &str = "SFT407";
pub const TEST_INLINE_PARAMETRIZE_VALUES_CODE: &str = "SFT408";
pub const TEST_NONEMPTY_PARAMETRIZE_VALUES_CODE: &str = "SFT411";
pub const TEST_NO_DICT_TEST_CASES_CODE: &str = "SFT412";
pub const TEST_DESCRIPTION_LAMBDA_IDS_CODE: &str = "SFT414";
pub const TEST_DESCRIPTION_FIELD_NAME: &str = "description";
pub const TEST_EXPECTED_FIELD_PREFIX: &str = "expected_";
pub const TEST_INIT_MODULE_NAME: &str = "__init__.py";
pub const TEST_MINIMUM_PARAMETRIZE_ARGUMENTS: u32 = 2;
pub const STAR_IMPORT_NAME: &str = "*";
pub const NATIVE_RULE_FACT_FAMILIES: &[(&str, &[&str])] = &[
    (PARAMETER_ANNOTATION_CODE, &["annotations"]),
    (RETURN_ANNOTATION_CODE, &["annotations"]),
    (MODULE_VARIABLE_ANNOTATION_CODE, &["annotations"]),
    (CLASS_ATTRIBUTE_ANNOTATION_CODE, &["annotations"]),
    (LOCAL_VARIABLE_ANNOTATION_CODE, &["annotations"]),
    (SINGLE_LINE_DOCSTRINGS_CODE, &["hygiene"]),
    (NO_STANDALONE_COMMENTS_CODE, &["comments"]),
    (NO_RAW_BUILTIN_RAISE_CODE, &["hygiene"]),
    (NO_ASSERT_IN_RUNTIME_CODE, &["hygiene"]),
    (NO_SWALLOWED_EXCEPTION_PROBE_CODE, &["hygiene"]),
    (
        NO_COMPLEX_COMPREHENSIONS_IN_TOOLING_CODE,
        &["complex_comprehensions"],
    ),
    (NO_UNNAMED_STRING_DECISIONS_CODE, &["hygiene"]),
    (NO_MAGIC_NUMERIC_COMPARISONS_CODE, &["hygiene"]),
    (NO_IMPORT_TIME_SIDE_EFFECTS_CODE, &["module_declarations"]),
    (VALIDATOR_MUST_NOT_RETURN_CODE, &["function_contracts"]),
    (PREDICATE_MUST_RETURN_BOOL_CODE, &["function_contracts"]),
    (VALUE_NAME_MUST_RETURN_VALUE_CODE, &["function_contracts"]),
    (
        ITERATOR_NAME_MUST_PRODUCE_ITERATOR_CODE,
        &["function_contracts"],
    ),
    (TOO_MANY_STATEMENTS_CODE, &["functions"]),
    (TOO_MANY_DISTINCT_CALLS_CODE, &["functions"]),
    (TOO_MANY_LOCALS_CODE, &["functions"]),
    (MAX_ARGUMENTS_CODE, &["functions"]),
    (MAX_STATEMENTS_GLOBAL_CODE, &["functions"]),
    (
        PARAMETER_MUTATION_IN_PHASE_HELPERS_CODE,
        &["parameter_mutations"],
    ),
    (DEFAULT_MUTATION_RETURN_CODE, &["parameter_mutations"]),
    (KEYWORD_ONLY_ARGUMENTS_CODE, &["functions"]),
    (NO_OUTER_STATE_MUTATION_CODE, &["outer_state_mutations"]),
    (NO_COMPLEX_COMPREHENSIONS_CODE, &["complex_comprehensions"]),
    (MUTABLE_RESULT_MODEL_CODE, &["dataclasses"]),
    (ABSOLUTE_IMPORTS_ONLY_CODE, &["references"]),
    (NO_STAR_IMPORTS_CODE, &["references"]),
    (NO_CROSS_FILE_HELPER_PRIVATE_CLASS_CODE, &["references"]),
    (PRIVATE_DEFINITION_ORDERING_CODE, &["module_declarations"]),
    (TEST_INIT_MODULE_EMPTY_CODE, &["test_module"]),
    (TEST_ABSOLUTE_IMPORTS_CODE, &["references"]),
    (TEST_NO_TOP_LEVEL_HELPERS_CODE, &["test_module"]),
    (
        TEST_NO_IF_IN_TESTS_CODE,
        &["test_functions", "function_conditionals"],
    ),
    (TEST_PRIVATE_CONSTANT_ORDER_CODE, &["test_module"]),
    (
        TEST_NO_COMPLEX_COMPREHENSIONS_CODE,
        &["complex_comprehensions"],
    ),
    (TEST_TYPES_DESCRIPTION_CODE, &["dataclasses"]),
    (TEST_TYPES_EXPECTED_FIELD_CODE, &["dataclasses"]),
    (TEST_LOCAL_TEST_TYPES_IMPORT_CODE, &["references"]),
    (TEST_FILE_NAME_CODE, &[]),
    (TEST_FUNCTION_NAME_CODE, &["test_functions"]),
    (TEST_DATACLASS_PARAMETRIZE_CODE, &["test_functions"]),
    (TEST_ACCEPTS_TEST_CASE_CODE, &["test_functions"]),
    (TEST_EXPECTED_FIELD_ASSERTION_CODE, &["test_functions"]),
    (TEST_PARAMETRIZE_ARGUMENTS_CODE, &["test_functions"]),
    (TEST_PARAMETRIZE_TEST_CASE_CODE, &["test_functions"]),
    (TEST_PARAMETRIZE_IDS_CODE, &["test_functions"]),
    (TEST_INLINE_PARAMETRIZE_VALUES_CODE, &["test_functions"]),
    (TEST_NONEMPTY_PARAMETRIZE_VALUES_CODE, &["test_functions"]),
    (TEST_NO_DICT_TEST_CASES_CODE, &["test_functions"]),
    (TEST_DESCRIPTION_LAMBDA_IDS_CODE, &["test_functions"]),
];
