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
pub const TEST_ABSOLUTE_IMPORTS_CODE: &str = "SFT102";
pub const TEST_NO_COMPLEX_COMPREHENSIONS_CODE: &str = "SFT106";
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
    (TEST_ABSOLUTE_IMPORTS_CODE, &["references"]),
    (
        TEST_NO_COMPLEX_COMPREHENSIONS_CODE,
        &["complex_comprehensions"],
    ),
];
