//! Shared byte-level constants for native fact extraction.

pub const NEWLINE_BYTE: u8 = b'\n';
pub const PYTHON_FILE_SUFFIX_BYTES: &[u8] = b".py";
pub const COMMENT_BYTE: u8 = b'#';
pub const OPEN_PAREN_BYTE: u8 = b'(';
pub const CLOSE_PAREN_BYTE: u8 = b')';
pub const MODELS_MODULE_NAME: &str = "strata.analysis.models";
pub const COMMENT_FACT_NAME: &str = "CommentFact";
pub const RECEIVER_NAMES: [&str; 2] = ["self", "cls"];
pub const ENUM_BASE_NAMES: [&str; 2] = ["Enum", "StrEnum"];
pub const DISCARD_NAME: &str = "_";
pub const MODULE_EXEMPT_NAMES: [&str; 4] =
    ["__all__", "__match_args__", "__slots__", "__version__"];
pub const CLASS_EXEMPT_NAMES: [&str; 3] = ["__match_args__", "__slots__", "__test__"];
pub const SOURCE_LOCATION_NAME: &str = "SourceLocation";
pub const ANNOTATION_FACTS_NAME: &str = "AnnotationFacts";
pub const MISSING_PARAMETER_ANNOTATION_NAME: &str = "MissingParameterAnnotationFact";
pub const MISSING_RETURN_ANNOTATION_NAME: &str = "MissingReturnAnnotationFact";
pub const MISSING_LOCAL_ANNOTATION_NAME: &str = "MissingLocalAnnotationFact";
pub const MISSING_VARIABLE_ANNOTATION_NAME: &str = "MissingVariableAnnotationFact";
pub const MODEL_BASE_NAMES: [&str; 1] = ["BaseModel"];
pub const TYPE_BASE_NAMES: [&str; 8] = [
    "Enum",
    "IntEnum",
    "StrEnum",
    "Flag",
    "IntFlag",
    "NamedTuple",
    "Protocol",
    "TypedDict",
];
pub const TYPE_CHECKING_NAME: &str = "TYPE_CHECKING";
pub const TYPE_ALIAS_NAME: &str = "TypeAlias";
pub const NEW_TYPE_NAME: &str = "NewType";
pub const FUTURE_MODULE_NAME: &str = "__future__";
pub const ALL_EXPORT_NAME: &str = "__all__";
pub const RULE_DECORATOR_NAME: &str = "rule";
pub const MAIN_ROLE_NAME: &str = "main";
pub const MODULE_NAME_VARIABLE: &str = "__name__";
pub const MAIN_MODULE_NAME: &str = "__main__";
pub const DATACLASS_DECORATOR_NAME: &str = "dataclass";
pub const ERROR_CLASS_SUFFIXES: [&str; 2] = ["Error", "Exception"];
pub const PRIVATE_NAME_PREFIX: &str = "_";
pub const MODULE_SEPARATOR: &str = ".";
pub const MODULE_DECLARATION_FACTS_NAME: &str = "ModuleDeclarationFacts";
pub const MODULE_STATEMENT_FACT_NAME: &str = "ModuleStatementFact";
pub const NAMED_CALL_FACT_NAME: &str = "NamedCallFact";
pub const TYPE_DECLARATION_FACT_NAME: &str = "TypeDeclarationFact";
pub const MISSING_ANNOTATION_CATEGORY: &str = "missing";
pub const NONE_ANNOTATION_CATEGORY: &str = "none";
pub const OTHER_ANNOTATION_CATEGORY: &str = "other";
pub const MISSING_ANNOTATION_DISPLAY: &str = "missing";
pub const RETURN_CATEGORY_PAIRS: [(&str, &str); 10] = [
    ("None", "none"),
    ("NoReturn", "none"),
    ("Never", "none"),
    ("bool", "bool"),
    ("TypeGuard", "type-guard"),
    ("TypeIs", "type-is"),
    ("Iterator", "iterator"),
    ("Generator", "generator"),
    ("AsyncIterator", "async-iterator"),
    ("AsyncGenerator", "async-generator"),
];
pub const FUNCTION_CONTRACT_FACT_NAME: &str = "FunctionContractFact";
pub const CONTROL_CHARACTER_LIMIT: u32 = 0x20;
pub const DELETE_CHARACTER: u32 = 0x7f;
pub const FLOAT_REPR_MIN_MAGNITUDE: f64 = 1e-4;
pub const FLOAT_REPR_MAX_MAGNITUDE: f64 = 1e16;
pub const ZERO_FLOAT: f64 = 0.0;
pub const MUTATOR_METHOD_NAMES: [&str; 9] = [
    "add",
    "append",
    "clear",
    "extend",
    "insert",
    "pop",
    "remove",
    "setdefault",
    "update",
];
pub const SETTER_DECORATOR_SUFFIX: &str = ".setter";
pub const DUNDER_AFFIX: &str = "__";
pub const FUNCTION_FACTS_NAME: &str = "FunctionFacts";
pub const FUNCTION_METRIC_FACT_NAME: &str = "FunctionMetricFact";
pub const PARAMETER_MUTATION_FACT_NAME: &str = "ParameterMutationFact";
pub const PARAMETER_MUTATION_OCCURRENCE_FACT_NAME: &str = "ParameterMutationOccurrenceFact";
pub const WILDCARD_IMPORT_NAME: &str = "*";
pub const OUTER_STATE_MUTATION_FACT_NAME: &str = "OuterStateMutationFact";
pub const SOURCE_POSITION_NAME: &str = "SourcePosition";
pub const SOURCE_RANGE_NAME: &str = "SourceRange";
pub const RAW_BUILTIN_RAISE_NAMES: [&str; 7] = [
    "AssertionError",
    "Exception",
    "KeyError",
    "NotImplementedError",
    "RuntimeError",
    "TypeError",
    "ValueError",
];
pub const EXCEPTION_CLASS_NAME: &str = "Exception";
pub const FROZENSET_FUNCTION_NAME: &str = "frozenset";
pub const TEST_CASE_LIST_NAME: &str = "TEST_CASES";
pub const TEST_CASE_LIST_SUFFIX: &str = "_TEST_CASES";
pub const TEST_FUNCTION_PREFIX: &str = "test_";
pub const IMPORT_FACT_NAME: &str = "ImportFact";
pub const IMPORT_ALIAS_FACT_NAME: &str = "ImportAliasFact";
pub const ATTRIBUTE_REFERENCE_FACT_NAME: &str = "AttributeReferenceFact";
pub const REFERENCE_FACTS_NAME: &str = "ReferenceFacts";
pub const PYTEST_MODULE_FACTS_NAME: &str = "PytestModuleFacts";
pub const HYGIENE_FACTS_NAME: &str = "HygieneFacts";
pub const FUNCTION_CONDITIONAL_FACT_NAME: &str = "FunctionConditionalFact";
pub const NEGATIVE_ONE_FLOAT: f64 = -1.0;
pub const ONE_FLOAT: f64 = 1.0;
pub const NO_RETURN_ANNOTATION_NAMES: [&str; 3] = ["Never", "NoReturn", "None"];
pub const FROZEN_KEYWORD_NAME: &str = "frozen";
pub const DATACLASS_FACT_NAME: &str = "DataclassFact";
pub const PROJECT_FUNCTION_FACT_NAME: &str = "ProjectFunctionFact";
pub const PROJECT_CALL_FACTS_NAME: &str = "ProjectCallFacts";
pub const DISCARDED_PROJECT_CALL_FACT_NAME: &str = "DiscardedProjectCallFact";
pub const STRATA_MODULE_NAME: &str = "strata";
pub const EVALUATE_RULE_NAME: &str = "evaluate_rule";
pub const RULE_CASE_NAME: &str = "RuleCase";
pub const PARAMETRIZE_NAME_PARTS: [&str; 3] = ["pytest", "mark", "parametrize"];
pub const PARAMETRIZE_DECORATOR_NAME: &str = "pytest.mark.parametrize";
pub const RULE_KEYWORD_NAME: &str = "rule";
pub const TEST_CASE_KEYWORD_NAME: &str = "test_case";
pub const IDS_KEYWORD_NAME: &str = "ids";
pub const CASE_PARAMETER_NAME: &str = "case";
pub const DESCRIPTION_ATTRIBUTE_NAME: &str = "description";
pub const EXPECTED_FIELD_PREFIX: &str = "expected_";
pub const MISSING_CASE_FORM: &str = "missing";
pub const LITERAL_CASE_FORM: &str = "literal";
pub const PARAMETER_CASE_FORM: &str = "parameter";
pub const LOCAL_CASE_FORM: &str = "local";
pub const DYNAMIC_CASE_FORM: &str = "dynamic";
pub const MINIMUM_PARAMETRIZE_ARGUMENTS: usize = 2;
pub const MINIMUM_EXPECTED_FIELD_CHAIN_PARTS: usize = 2;
pub const STATIC_REFERENCE_FACT_NAME: &str = "StaticReferenceFact";
pub const EVALUATE_RULE_CALL_FACT_NAME: &str = "EvaluateRuleCallFact";
pub const PARAMETRIZE_DIMENSION_FACT_NAME: &str = "ParametrizeDimensionFact";
pub const PYTEST_FUNCTION_FACT_NAME: &str = "PytestFunctionFact";
pub const PARAMETRIZE_FACT_NAME: &str = "ParametrizeFact";
pub const PARAMETRIZE_CASE_FACT_NAME: &str = "ParametrizeCaseFact";
pub const TYPES_MODULE_NAME: &str = "strata.analysis.types";
pub const RULE_CASE_FORM_NAME: &str = "RuleCaseForm";
pub const RETURN_ANNOTATION_CATEGORY_NAME: &str = "ReturnAnnotationCategory";
pub const ASSIGNMENT_REFERENCE_FACT_NAME: &str = "AssignmentReferenceFact";
pub const CLASS_DECLARATION_FACT_NAME: &str = "ClassDeclarationFact";
pub const CLASS_METHOD_FACT_NAME: &str = "ClassMethodFact";
pub const COMPARISON_FACT_NAME: &str = "ComparisonFact";
pub const DEFINITION_IDENTITY_NAME: &str = "DefinitionIdentity";
pub const LITERAL_ARGUMENT_FACT_NAME: &str = "LiteralArgumentFact";
pub const LOCAL_CALL_EDGE_FACT_NAME: &str = "LocalCallEdgeFact";
pub const QUALIFIED_REFERENCE_FACT_NAME: &str = "QualifiedReferenceFact";
