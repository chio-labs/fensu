//! Generated configuration defaults. Do not edit by hand.

#[rustfmt::skip]
pub(crate) const DEFAULT_THRESHOLDS: &[(&str, u32)] = &[
    ("max_statements", 40),
    ("max_distinct_calls", 20),
    ("max_locals", 20),
    ("max_file_lines", 2000),
    ("max_helpers_container_modules", 10),
    ("max_main_container_modules", 20),
    ("max_role_depth", 1),
    ("max_positional_args", 1),
    ("max_arguments", 10),
    ("max_statements_global", 70),
    ("max_script_entrypoint_lines", 80),
    ("min_shared_domain_prefix_packages", 2),
    ("min_custom_rule_test_cases", 1),
];

#[rustfmt::skip]
pub(crate) const DEFAULT_CONTRACTS: &[(&str, &str)] = &[
    ("validate_*", "no-return"),
    ("enforce_*", "no-return"),
    ("is_*", "returns-bool"),
    ("has_*", "returns-bool"),
    ("can_*", "returns-bool"),
    ("supports_*", "returns-bool"),
    ("get_*", "returns-value"),
    ("to_*", "returns-value"),
    ("as_*", "returns-value"),
    ("iter_*", "returns-iterator"),
];

#[rustfmt::skip]
pub(crate) const DEFAULT_TEST_PATHS: &[&str] = &[
    "tests",
];

#[rustfmt::skip]
pub(crate) const DEFAULT_TEST_SCOPES: &[&str] = &[
    "unit",
    "integration",
    "e2e",
];

#[rustfmt::skip]
pub(crate) const DEFAULT_SELECT: &[&str] = &[
    "FF",
];

#[rustfmt::skip]
pub(crate) const DEFAULT_WARN: &[&str] = &[
];

#[rustfmt::skip]
pub(crate) const DEFAULT_IGNORE: &[&str] = &[
];

pub(crate) const DEFAULT_CACHE_ENABLED: bool = true;

pub(crate) const DEFAULT_CACHE_REQUIRE_CACHEABLE: bool = false;

pub(crate) const DEFAULT_EXPERIMENTAL_MEMORY: bool = false;

pub(crate) const DEFAULT_MEMORY_ARCHIVE_DAYS: u64 = 7;

pub(crate) const SKILLS_METADATA_PROTOCOL_VERSION: u32 = 3;

#[rustfmt::skip]
pub(crate) const CONFIG_ROLE_NAMES: &[&str] = &[
    "classes",
    "constants",
    "exceptions",
    "helpers",
    "main",
    "models",
    "rules",
    "types",
];

#[rustfmt::skip]
pub(crate) const CONTRACT_BEHAVIORS: &[&str] = &[
    "no-return",
    "returns-bool",
    "returns-iterator",
    "returns-value",
];

#[rustfmt::skip]
pub(crate) const RULE_CONFIGURATION_INPUTS: &[&str] = &[
    "roots",
    "test_scopes",
    "tests",
    "tooling",
];
