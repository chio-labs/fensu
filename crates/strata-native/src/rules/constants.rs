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
pub const MEANINGFUL_PROJECT_RESULT_DISCARDED_CODE: &str = "SFS101";
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
pub const NO_SIBLING_PACKAGE_INTERNALS_CODE: &str = "SFL101";
pub const NO_CROSS_PACKAGE_INTERNALS_CODE: &str = "SFL102";
pub const NO_INTERNAL_PUBLIC_SURFACE_IMPORTS_CODE: &str = "SFL103";
pub const NO_CROSS_DOMAIN_PRIVATE_MAIN_IMPORTS_CODE: &str = "SFL104";
pub const NO_CROSS_FILE_HELPER_PRIVATE_CLASS_CODE: &str = "SFL110";
pub const NO_RUNTIME_IMPORTS_FROM_TOOLING_CODE: &str = "SFL301";
pub const MODELS_ONLY_MODELS_CODE: &str = "SFR001";
pub const TYPES_ONLY_TYPES_CODE: &str = "SFR002";
pub const CONSTANTS_ONLY_CONSTANTS_CODE: &str = "SFR003";
pub const EXCEPTIONS_ONLY_EXCEPTIONS_CODE: &str = "SFR004";
pub const MODEL_DECLARATION_OUTSIDE_MODELS_CODE: &str = "SFR101";
pub const TYPE_DECLARATION_OUTSIDE_TYPES_CODE: &str = "SFR102";
pub const CONSTANT_OUTSIDE_CONSTANTS_CODE: &str = "SFR103";
pub const EXCEPTION_DECLARATION_OUTSIDE_EXCEPTIONS_CODE: &str = "SFR104";
pub const BANNED_GENERIC_FILENAME_CODE: &str = "SFR201";
pub const HELPERS_MODULE_NAME_CODE: &str = "SFR202";
pub const CLASSES_MODULE_NAME_CODE: &str = "SFR203";
pub const BANNED_GENERIC_PACKAGE_NAME_CODE: &str = "SFR204";
pub const HELPERS_CLASSES_FILE_PRIVATE_CODE: &str = "SFR205";
pub const HELPERS_RESERVED_ROLE_FILENAMES_CODE: &str = "SFR303";
pub const NESTED_DIRECT_MODULES_CODE: &str = "SFR304";
pub const NESTED_DIRECT_SUBPACKAGES_CODE: &str = "SFR305";
pub const TOP_LEVEL_DIRECT_MODULES_CODE: &str = "SFR307";
pub const ENTRY_MODULE_SHAPE_CODE: &str = "SFR401";
pub const INIT_MODULE_EMPTY_CODE: &str = "SFR402";
pub const NO_REEXPORT_SHIM_CODE: &str = "SFR403";
pub const NO_INTERNAL_HELPER_EXPORTS_CODE: &str = "SFR404";
pub const MAIN_ENTRY_NAME_COLLISION_CODE: &str = "SFR405";
pub const PUBLIC_SURFACE_SHAPE_CODE: &str = "SFR406";
pub const CLASSES_ONE_CLASS_PER_MODULE_CODE: &str = "SFR501";
pub const HELPERS_PACKAGE_SHAPE_CODE: &str = "SFR502";
pub const PRIVATE_DEFINITION_ORDERING_CODE: &str = "SFR503";
pub const SOURCE_FILE_LINE_COUNT_CODE: &str = "SFR601";
pub const TOOLING_ENTRYPOINT_SHAPE_CODE: &str = "SFR701";
pub const TOOLING_ENTRYPOINT_DELEGATION_CODE: &str = "SFR702";
pub const TOOLING_ENTRYPOINT_LINE_COUNT_CODE: &str = "SFR703";
pub const RULES_ROLE_CONTENT_CODE: &str = "SFR704";
pub const TOOLING_PACKAGE_LAYOUT_CODE: &str = "SFR705";
pub const DESCRIPTIVE_RULE_MODULE_NAMES_CODE: &str = "SFR706";
pub const CUSTOM_RULE_TEST_COVERAGE_CODE: &str = "SFR707";
pub const TEST_LAYOUT_CODE: &str = "SFT001";
pub const TEST_SCOPE_CODE: &str = "SFT002";
pub const TEST_MIRRORED_ROOT_CODE: &str = "SFT003";
pub const TEST_SRC_MIRROR_DEPTH_CODE: &str = "SFT004";
pub const TEST_SRC_PACKAGE_EXISTS_CODE: &str = "SFT005";
pub const TEST_SRC_AREA_EXISTS_CODE: &str = "SFT006";
pub const TEST_SCRIPTS_MIRROR_DEPTH_CODE: &str = "SFT007";
pub const TEST_SCRIPTS_AREA_EXISTS_CODE: &str = "SFT008";
pub const TEST_INIT_MODULE_EMPTY_CODE: &str = "SFT101";
pub const TEST_ABSOLUTE_IMPORTS_CODE: &str = "SFT102";
pub const TEST_NO_TOP_LEVEL_HELPERS_CODE: &str = "SFT103";
pub const TEST_NO_IF_IN_TESTS_CODE: &str = "SFT104";
pub const TEST_PRIVATE_CONSTANT_ORDER_CODE: &str = "SFT105";
pub const TEST_NO_COMPLEX_COMPREHENSIONS_CODE: &str = "SFT106";
pub const TEST_TYPES_DESCRIPTION_CODE: &str = "SFT201";
pub const TEST_TYPES_EXPECTED_FIELD_CODE: &str = "SFT202";
pub const TEST_LOCAL_TEST_TYPES_IMPORT_CODE: &str = "SFT203";
pub const TEST_LOCAL_TEST_TYPES_FILE_CODE: &str = "SFT204";
pub const TEST_FILE_NAME_CODE: &str = "SFT301";
pub const TEST_FUNCTION_NAME_CODE: &str = "SFT302";
pub const TEST_DATACLASS_PARAMETRIZE_CODE: &str = "SFT401";
pub const TEST_ACCEPTS_TEST_CASE_CODE: &str = "SFT402";
pub const TEST_CASE_ANNOTATION_CODE: &str = "SFT403";
pub const TEST_EXPECTED_FIELD_ASSERTION_CODE: &str = "SFT404";
pub const TEST_PARAMETRIZE_ARGUMENTS_CODE: &str = "SFT405";
pub const TEST_PARAMETRIZE_TEST_CASE_CODE: &str = "SFT406";
pub const TEST_PARAMETRIZE_IDS_CODE: &str = "SFT407";
pub const TEST_INLINE_PARAMETRIZE_VALUES_CODE: &str = "SFT408";
pub const TEST_NONEMPTY_PARAMETRIZE_VALUES_CODE: &str = "SFT411";
pub const TEST_NO_DICT_TEST_CASES_CODE: &str = "SFT412";
pub const TEST_LOCAL_TEST_CASE_CONSTRUCTORS_CODE: &str = "SFT413";
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
    (
        MEANINGFUL_PROJECT_RESULT_DISCARDED_CODE,
        &["project_calls", "project_functions"],
    ),
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
    (NO_SIBLING_PACKAGE_INTERNALS_CODE, &["references"]),
    (NO_CROSS_PACKAGE_INTERNALS_CODE, &["references"]),
    (NO_INTERNAL_PUBLIC_SURFACE_IMPORTS_CODE, &["references"]),
    (NO_CROSS_DOMAIN_PRIVATE_MAIN_IMPORTS_CODE, &["references"]),
    (NO_CROSS_FILE_HELPER_PRIVATE_CLASS_CODE, &["references"]),
    (NO_RUNTIME_IMPORTS_FROM_TOOLING_CODE, &["references"]),
    (MODELS_ONLY_MODELS_CODE, &["module_declarations"]),
    (TYPES_ONLY_TYPES_CODE, &["module_declarations"]),
    (CONSTANTS_ONLY_CONSTANTS_CODE, &["module_declarations"]),
    (EXCEPTIONS_ONLY_EXCEPTIONS_CODE, &["module_declarations"]),
    (
        MODEL_DECLARATION_OUTSIDE_MODELS_CODE,
        &["module_declarations"],
    ),
    (
        TYPE_DECLARATION_OUTSIDE_TYPES_CODE,
        &["module_declarations"],
    ),
    (CONSTANT_OUTSIDE_CONSTANTS_CODE, &["module_declarations"]),
    (
        EXCEPTION_DECLARATION_OUTSIDE_EXCEPTIONS_CODE,
        &["module_declarations"],
    ),
    (BANNED_GENERIC_FILENAME_CODE, &[]),
    (HELPERS_MODULE_NAME_CODE, &[]),
    (CLASSES_MODULE_NAME_CODE, &[]),
    (BANNED_GENERIC_PACKAGE_NAME_CODE, &[]),
    (HELPERS_CLASSES_FILE_PRIVATE_CODE, &["module_declarations"]),
    (HELPERS_RESERVED_ROLE_FILENAMES_CODE, &[]),
    (NESTED_DIRECT_MODULES_CODE, &[]),
    (NESTED_DIRECT_SUBPACKAGES_CODE, &[]),
    (TOP_LEVEL_DIRECT_MODULES_CODE, &[]),
    (ENTRY_MODULE_SHAPE_CODE, &["module_declarations"]),
    (INIT_MODULE_EMPTY_CODE, &["module_declarations"]),
    (NO_REEXPORT_SHIM_CODE, &["module_declarations"]),
    (NO_INTERNAL_HELPER_EXPORTS_CODE, &["module_declarations"]),
    (MAIN_ENTRY_NAME_COLLISION_CODE, &[]),
    (PUBLIC_SURFACE_SHAPE_CODE, &["module_declarations"]),
    (CLASSES_ONE_CLASS_PER_MODULE_CODE, &["module_declarations"]),
    (HELPERS_PACKAGE_SHAPE_CODE, &[]),
    (PRIVATE_DEFINITION_ORDERING_CODE, &["module_declarations"]),
    (SOURCE_FILE_LINE_COUNT_CODE, &[]),
    (TOOLING_ENTRYPOINT_SHAPE_CODE, &["module_declarations"]),
    (TOOLING_ENTRYPOINT_DELEGATION_CODE, &["module_declarations"]),
    (TOOLING_ENTRYPOINT_LINE_COUNT_CODE, &[]),
    (RULES_ROLE_CONTENT_CODE, &["module_declarations"]),
    (TOOLING_PACKAGE_LAYOUT_CODE, &[]),
    (DESCRIPTIVE_RULE_MODULE_NAMES_CODE, &[]),
    (CUSTOM_RULE_TEST_COVERAGE_CODE, &[]),
    (TEST_LAYOUT_CODE, &[]),
    (TEST_SCOPE_CODE, &[]),
    (TEST_MIRRORED_ROOT_CODE, &[]),
    (TEST_SRC_MIRROR_DEPTH_CODE, &[]),
    (TEST_SRC_PACKAGE_EXISTS_CODE, &[]),
    (TEST_SRC_AREA_EXISTS_CODE, &[]),
    (TEST_SCRIPTS_MIRROR_DEPTH_CODE, &[]),
    (TEST_SCRIPTS_AREA_EXISTS_CODE, &[]),
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
    (TEST_LOCAL_TEST_TYPES_FILE_CODE, &[]),
    (TEST_FILE_NAME_CODE, &[]),
    (TEST_FUNCTION_NAME_CODE, &["test_functions"]),
    (TEST_DATACLASS_PARAMETRIZE_CODE, &["test_functions"]),
    (TEST_ACCEPTS_TEST_CASE_CODE, &["test_functions"]),
    (TEST_CASE_ANNOTATION_CODE, &["test_functions", "references"]),
    (TEST_EXPECTED_FIELD_ASSERTION_CODE, &["test_functions"]),
    (TEST_PARAMETRIZE_ARGUMENTS_CODE, &["test_functions"]),
    (TEST_PARAMETRIZE_TEST_CASE_CODE, &["test_functions"]),
    (TEST_PARAMETRIZE_IDS_CODE, &["test_functions"]),
    (TEST_INLINE_PARAMETRIZE_VALUES_CODE, &["test_functions"]),
    (TEST_NONEMPTY_PARAMETRIZE_VALUES_CODE, &["test_functions"]),
    (TEST_NO_DICT_TEST_CASES_CODE, &["test_functions"]),
    (
        TEST_LOCAL_TEST_CASE_CONSTRUCTORS_CODE,
        &["test_functions", "references"],
    ),
    (TEST_DESCRIPTION_LAMBDA_IDS_CODE, &["test_functions"]),
];
