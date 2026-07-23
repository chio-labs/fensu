//! Native rule registrations and their consumed public fact families.

pub const PARAMETER_ANNOTATION_CODE: &str = "FFA001";
pub const RETURN_ANNOTATION_CODE: &str = "FFA002";
pub const MODULE_VARIABLE_ANNOTATION_CODE: &str = "FFA101";
pub const CLASS_ATTRIBUTE_ANNOTATION_CODE: &str = "FFA102";
pub const LOCAL_VARIABLE_ANNOTATION_CODE: &str = "FFA103";
pub const SINGLE_LINE_DOCSTRINGS_CODE: &str = "FFH001";
pub const NO_STANDALONE_COMMENTS_CODE: &str = "FFH002";
pub const NO_RAW_BUILTIN_RAISE_CODE: &str = "FFH003";
pub const NO_ASSERT_IN_RUNTIME_CODE: &str = "FFH004";
pub const NO_SWALLOWED_EXCEPTION_PROBE_CODE: &str = "FFH005";
pub const NO_COMPLEX_COMPREHENSIONS_IN_TOOLING_CODE: &str = "FFH006";
pub const NO_UNNAMED_STRING_DECISIONS_CODE: &str = "FFH007";
pub const NO_MAGIC_NUMERIC_COMPARISONS_CODE: &str = "FFH008";
pub const NO_IMPORT_TIME_SIDE_EFFECTS_CODE: &str = "FFH009";
pub const TOO_MANY_STATEMENTS_CODE: &str = "FFS001";
pub const TOO_MANY_DISTINCT_CALLS_CODE: &str = "FFS002";
pub const TOO_MANY_LOCALS_CODE: &str = "FFS003";
pub const MEANINGFUL_PROJECT_RESULT_DISCARDED_CODE: &str = "FFS101";
pub const MAX_ARGUMENTS_CODE: &str = "FFS010";
pub const MAX_STATEMENTS_GLOBAL_CODE: &str = "FFS011";
pub const PARAMETER_MUTATION_IN_PHASE_HELPERS_CODE: &str = "FFS102";
pub const DEFAULT_MUTATION_RETURN_CODE: &str = "FFS110";
pub const KEYWORD_ONLY_ARGUMENTS_CODE: &str = "FFS120";
pub const NO_OUTER_STATE_MUTATION_CODE: &str = "FFS130";
pub const NO_COMPLEX_COMPREHENSIONS_CODE: &str = "FFS131";
pub const MUTABLE_RESULT_MODEL_CODE: &str = "FFS201";
pub const VALIDATOR_MUST_NOT_RETURN_CODE: &str = "FFN001";
pub const PREDICATE_MUST_RETURN_BOOL_CODE: &str = "FFN002";
pub const VALUE_NAME_MUST_RETURN_VALUE_CODE: &str = "FFN003";
pub const ITERATOR_NAME_MUST_PRODUCE_ITERATOR_CODE: &str = "FFN004";
pub const ABSOLUTE_IMPORTS_ONLY_CODE: &str = "FFL001";
pub const NO_STAR_IMPORTS_CODE: &str = "FFL002";
pub const NO_SIBLING_PACKAGE_INTERNALS_CODE: &str = "FFL101";
pub const NO_CROSS_PACKAGE_INTERNALS_CODE: &str = "FFL102";
pub const NO_INTERNAL_PUBLIC_SURFACE_IMPORTS_CODE: &str = "FFL103";
pub const NO_CROSS_DOMAIN_PRIVATE_MAIN_IMPORTS_CODE: &str = "FFL104";
pub const PUBLIC_MAIN_ENTRY_EXTERNAL_USE_CODE: &str = "FFL105";
pub const NO_CROSS_FILE_HELPER_PRIVATE_CLASS_CODE: &str = "FFL110";
pub const NO_RUNTIME_IMPORTS_FROM_TOOLING_CODE: &str = "FFL301";
pub const MODELS_ONLY_MODELS_CODE: &str = "FFR001";
pub const TYPES_ONLY_TYPES_CODE: &str = "FFR002";
pub const CONSTANTS_ONLY_CONSTANTS_CODE: &str = "FFR003";
pub const EXCEPTIONS_ONLY_EXCEPTIONS_CODE: &str = "FFR004";
pub const MODEL_DECLARATION_OUTSIDE_MODELS_CODE: &str = "FFR101";
pub const TYPE_DECLARATION_OUTSIDE_TYPES_CODE: &str = "FFR102";
pub const CONSTANT_OUTSIDE_CONSTANTS_CODE: &str = "FFR103";
pub const EXCEPTION_DECLARATION_OUTSIDE_EXCEPTIONS_CODE: &str = "FFR104";
pub const BANNED_GENERIC_FILENAME_CODE: &str = "FFR201";
pub const HELPERS_MODULE_NAME_CODE: &str = "FFR202";
pub const CLASSES_MODULE_NAME_CODE: &str = "FFR203";
pub const BANNED_GENERIC_PACKAGE_NAME_CODE: &str = "FFR204";
pub const HELPERS_CLASSES_FILE_PRIVATE_CODE: &str = "FFR205";
pub const HELPERS_PACKAGE_LAYOUT_CODE: &str = "FFR301";
pub const MAIN_PACKAGE_LAYOUT_CODE: &str = "FFR302";
pub const HELPERS_RESERVED_ROLE_FILENAMES_CODE: &str = "FFR303";
pub const NESTED_DIRECT_MODULES_CODE: &str = "FFR304";
pub const NESTED_DIRECT_SUBPACKAGES_CODE: &str = "FFR305";
pub const TOP_LEVEL_DIRECT_MODULES_CODE: &str = "FFR307";
pub const TOP_LEVEL_DOMAIN_SHAPE_CODE: &str = "FFR306";
pub const SHARED_DOMAIN_PREFIX_CODE: &str = "FFR308";
pub const LEAF_MAIN_BOUNDARY_CODE: &str = "FFR309";
pub const ENTRY_MODULE_SHAPE_CODE: &str = "FFR401";
pub const INIT_MODULE_EMPTY_CODE: &str = "FFR402";
pub const NO_REEXPORT_SHIM_CODE: &str = "FFR403";
pub const NO_INTERNAL_HELPER_EXPORTS_CODE: &str = "FFR404";
pub const MAIN_ENTRY_NAME_COLLISION_CODE: &str = "FFR405";
pub const PUBLIC_SURFACE_SHAPE_CODE: &str = "FFR406";
pub const CLASSES_ONE_CLASS_PER_MODULE_CODE: &str = "FFR501";
pub const HELPERS_PACKAGE_SHAPE_CODE: &str = "FFR502";
pub const PRIVATE_DEFINITION_ORDERING_CODE: &str = "FFR503";
pub const SOURCE_FILE_LINE_COUNT_CODE: &str = "FFR601";
pub const TOOLING_ENTRYPOINT_SHAPE_CODE: &str = "FFR701";
pub const TOOLING_ENTRYPOINT_DELEGATION_CODE: &str = "FFR702";
pub const TOOLING_ENTRYPOINT_LINE_COUNT_CODE: &str = "FFR703";
pub const RULES_ROLE_CONTENT_CODE: &str = "FFR704";
pub const TOOLING_PACKAGE_LAYOUT_CODE: &str = "FFR705";
pub const DESCRIPTIVE_RULE_MODULE_NAMES_CODE: &str = "FFR706";
pub const CUSTOM_RULE_TEST_COVERAGE_CODE: &str = "FFR707";
pub const TEST_LAYOUT_CODE: &str = "FFT001";
pub const TEST_SCOPE_CODE: &str = "FFT002";
pub const TEST_MIRRORED_ROOT_CODE: &str = "FFT003";
pub const TEST_SRC_MIRROR_DEPTH_CODE: &str = "FFT004";
pub const TEST_SRC_PACKAGE_EXISTS_CODE: &str = "FFT005";
pub const TEST_SRC_AREA_EXISTS_CODE: &str = "FFT006";
pub const TEST_SCRIPTS_MIRROR_DEPTH_CODE: &str = "FFT007";
pub const TEST_SCRIPTS_AREA_EXISTS_CODE: &str = "FFT008";
pub const TEST_INIT_MODULE_EMPTY_CODE: &str = "FFT101";
pub const TEST_ABSOLUTE_IMPORTS_CODE: &str = "FFT102";
pub const TEST_NO_TOP_LEVEL_HELPERS_CODE: &str = "FFT103";
pub const TEST_NO_IF_IN_TESTS_CODE: &str = "FFT104";
pub const TEST_PRIVATE_CONSTANT_ORDER_CODE: &str = "FFT105";
pub const TEST_NO_COMPLEX_COMPREHENSIONS_CODE: &str = "FFT106";
pub const TEST_TYPES_DESCRIPTION_CODE: &str = "FFT201";
pub const TEST_TYPES_EXPECTED_FIELD_CODE: &str = "FFT202";
pub const TEST_LOCAL_TEST_TYPES_IMPORT_CODE: &str = "FFT203";
pub const TEST_LOCAL_TEST_TYPES_FILE_CODE: &str = "FFT204";
pub const TEST_FILE_NAME_CODE: &str = "FFT301";
pub const TEST_FUNCTION_NAME_CODE: &str = "FFT302";
pub const TEST_DATACLASS_PARAMETRIZE_CODE: &str = "FFT401";
pub const TEST_ACCEPTS_TEST_CASE_CODE: &str = "FFT402";
pub const TEST_CASE_ANNOTATION_CODE: &str = "FFT403";
pub const TEST_EXPECTED_FIELD_ASSERTION_CODE: &str = "FFT404";
pub const TEST_PARAMETRIZE_ARGUMENTS_CODE: &str = "FFT405";
pub const TEST_PARAMETRIZE_TEST_CASE_CODE: &str = "FFT406";
pub const TEST_PARAMETRIZE_IDS_CODE: &str = "FFT407";
pub const TEST_INLINE_PARAMETRIZE_VALUES_CODE: &str = "FFT408";
pub const TEST_NONEMPTY_PARAMETRIZE_VALUES_CODE: &str = "FFT411";
pub const TEST_NO_DICT_TEST_CASES_CODE: &str = "FFT412";
pub const TEST_LOCAL_TEST_CASE_CONSTRUCTORS_CODE: &str = "FFT413";
pub const TEST_DESCRIPTION_LAMBDA_IDS_CODE: &str = "FFT414";
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
    (PUBLIC_MAIN_ENTRY_EXTERNAL_USE_CODE, &["references"]),
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
    (HELPERS_PACKAGE_LAYOUT_CODE, &[]),
    (MAIN_PACKAGE_LAYOUT_CODE, &[]),
    (HELPERS_RESERVED_ROLE_FILENAMES_CODE, &[]),
    (NESTED_DIRECT_MODULES_CODE, &[]),
    (NESTED_DIRECT_SUBPACKAGES_CODE, &[]),
    (TOP_LEVEL_DIRECT_MODULES_CODE, &[]),
    (TOP_LEVEL_DOMAIN_SHAPE_CODE, &[]),
    (SHARED_DOMAIN_PREFIX_CODE, &[]),
    (LEAF_MAIN_BOUNDARY_CODE, &[]),
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
pub const NATIVE_RULE_OPTIONS: &[(&str, &[&str])] = &[];
