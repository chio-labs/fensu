pub(crate) const COLOR_ALWAYS: &str = "always";
pub(crate) const COLOR_AUTO: &str = "auto";
pub(crate) const COLOR_NEVER: &str = "never";
pub(crate) const GLOB_ALL: &str = "**";
pub(crate) const OPTION_COLOR: &str = "--color";
pub(crate) const OWNER_FILE: &str = "file";
pub(crate) const OWNER_PACKAGE: &str = "package";
pub(crate) const ROLE_HELPERS: &str = "_helpers";
pub(crate) const ROLE_MAIN: &str = "main";
pub(crate) const ROLE_RULES: &str = "rules";
pub(crate) const SCOPE_TEST: &str = "test";
pub(crate) const SCOPE_TOOLING: &str = "tooling";
pub(crate) const STEM_INIT: &str = "__init__";
pub(crate) const SUFFIX_INIT: &str = "__init__.py";
pub(crate) const VALUE_TRUE: &str = "true";
pub(crate) const CONFIG_FENSU_FILE: &str = "fensu.toml";
pub(crate) const CONFIG_PYPROJECT_FILE: &str = "pyproject.toml";
pub(crate) const CONFIG_PYPROJECT_HEADER: &str = "[tool.fensu]";
pub(crate) const DEFAULT_MEMORY_ARCHIVE_DAYS: u64 = 7;
pub(crate) const MAX_CORE_SELECTOR_SUFFIX: usize = 4;
pub(crate) const PYTHON_CACHE_DIRECTORY: &str = "__pycache__";
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
pub(crate) const CONFIG_ROLE_NAMES: &[&str] = &[
    "classes",
    "constants",
    "entry",
    "exceptions",
    "helpers",
    "main",
    "models",
    "rules",
    "types",
];
pub(crate) const CONTRACT_BEHAVIORS: &[&str] = &[
    "no-return",
    "returns-bool",
    "returns-value",
    "returns-iterator",
];
