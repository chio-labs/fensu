//! Thresholds and name tables for the structure checker.

pub const MAX_FILE_LINES: usize = 400;
pub const MAX_DECLARATION_FILE_LINES: usize = 80;
pub const MAX_HELPER_CONTAINER_MODULES: usize = 10;
pub const MAX_MAIN_CONTAINER_MODULES: usize = 20;
pub const MAX_ENTRY_PRIVATE_FUNCTIONS: usize = 2;
pub const MAX_CONTAINER_COMPONENT_DEPTH: usize = 2;
pub const MIN_DOMAIN_SEGMENTS: usize = 2;
pub const MAX_ARGUMENTS: usize = 10;
pub const MAX_STATEMENTS_GLOBAL: usize = 70;
pub const MAX_STATEMENTS_ENTRY: usize = 40;
pub const MAX_DISTINCT_CALLS_ENTRY: usize = 20;
pub const MAX_LOCALS_ENTRY: usize = 20;
pub const TOOLING_CRATE_NAME: &str = "strata-structure-checker";
pub const BANNED_FILE_STEMS: &[&str] = &[
    "base",
    "common",
    "helper",
    "manager",
    "misc",
    "processor",
    "shared",
    "util",
    "utils",
];
pub const BANNED_DIRECTORY_NAMES: &[&str] = &[
    "base",
    "common",
    "helper",
    "manager",
    "misc",
    "processor",
    "shared",
    "util",
    "utils",
];
pub const ROLE_FILE_NAMES: &[&str] = &[
    "constants.rs",
    "errors.rs",
    "mod.rs",
    "models.rs",
    "types.rs",
];
pub const CONTAINER_DIRECTORY_NAMES: &[&str] = &["helpers", "main"];
pub const HELPERS_DIRECTORY: &str = "helpers";
pub const MAIN_DIRECTORY: &str = "main";
pub const MOD_FILE: &str = "mod.rs";
pub const LIB_FILE: &str = "lib.rs";
pub const MAIN_FILE: &str = "main.rs";
pub const HELPERS_FILE: &str = "helpers.rs";
pub const MODELS_FILE: &str = "models.rs";
pub const TYPES_FILE: &str = "types.rs";
pub const CONSTANTS_FILE: &str = "constants.rs";
pub const ERRORS_FILE: &str = "errors.rs";
pub const TEST_TYPES_FILE: &str = "test_types.rs";
pub const SOURCE_DIRECTORY: &str = "src";
pub const TESTS_DIRECTORY: &str = "tests";
pub const CARGO_MANIFEST_FILE: &str = "Cargo.toml";
pub const RUST_SUFFIX: &str = "rs";
pub const SELF_MODULE: &str = "self";
pub const SUPER_MODULE: &str = "super";
pub const PANIC_EXTRACTION_METHODS: &[&str] = &["unwrap", "unwrap_err", "expect", "expect_err"];
pub const TEST_PANIC_EXTRACTION_METHODS: &[&str] = &["unwrap", "unwrap_err"];
pub const PANIC_MACROS: &[&str] = &["panic", "todo", "unimplemented", "unreachable"];
pub const ASSERT_MACROS: &[&str] = &[
    "assert",
    "assert_eq",
    "assert_ne",
    "debug_assert",
    "debug_assert_eq",
    "debug_assert_ne",
];
pub const STDIO_MACROS: &[&str] = &["dbg", "eprint", "eprintln", "print", "println"];
pub const FORBID_ATTRIBUTE: &str = "forbid";
pub const UNSAFE_CODE_LINT: &str = "unsafe_code";
pub const TEST_CASES_BINDING: &str = "test_cases";
pub const TEST_CASE_LOOP_VARIABLE: &str = "test_case";
pub const CASE_RUNNER_NAME: &str = "run_cases";
pub const MODULE_CASES_CONSTANT: &str = "TEST_CASES";
pub const TEST_CASE_STRUCT_SUFFIX: &str = "TestCase";
pub const ERROR_TYPE_SUFFIX: &str = "Error";
pub const DESCRIPTION_FIELD: &str = "description";
pub const EXPECTED_FIELD_PREFIX: &str = "expected_";
pub const DEBUG_DERIVE: &str = "Debug";
pub const BOOL_RETURN_PREFIXES: &[&str] = &["can_", "has_", "is_", "supports_"];
pub const VALUE_RETURN_PREFIXES: &[&str] = &["as_", "to_"];
pub const NO_RETURN_PREFIXES: &[&str] = &["enforce_", "validate_"];
pub const ITERATOR_RETURN_PREFIX: &str = "iter_";
pub const RESULT_TYPE: &str = "Result";
pub const ITERATOR_TYPE: &str = "Iterator";
pub const DISCOURAGED_GETTER_PREFIX: &str = "get_";
pub const ALLOWED_COMPARISON_NUMBERS: &[&str] = &["0", "1"];
pub const ITERATOR_TYPE_NAMES: &[&str] = &["Iter", "IterMut", "IntoIter", ITERATOR_TYPE];
pub const DEPENDENCY_TABLE_NAMES: &[&str] =
    &["dependencies", "dev-dependencies", "build-dependencies"];
pub const TARGET_KEY: &str = "target";
pub const DEPENDENCIES_KEY: &str = "dependencies";
pub const REQUIRED_RUST_LINTS: &[(&str, &str)] = &[
    ("unsafe_code", "forbid"),
    ("unreachable_pub", "deny"),
    ("unused_must_use", "deny"),
];
pub const REQUIRED_CLIPPY_LINTS: &[(&str, &str)] = &[("await_holding_lock", "deny")];
pub const WORKSPACE_KEY: &str = "workspace";
pub const MEMBERS_KEY: &str = "members";
pub const LINTS_KEY: &str = "lints";
pub const RUST_KEY: &str = "rust";
pub const CLIPPY_KEY: &str = "clippy";
pub const PACKAGE_KEY: &str = "package";
pub const NAME_KEY: &str = "name";
pub const VERSION_KEY: &str = "version";
pub const GIT_KEY: &str = "git";
pub const REV_KEY: &str = "rev";
pub const PATH_KEY: &str = "path";
pub const WILDCARD_VERSION: &str = "*";
pub const ALLOW_ATTRIBUTE: &str = "allow";
pub const EXPECT_ATTRIBUTE: &str = "expect";
