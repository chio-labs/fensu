pub(crate) const COLOR_ALWAYS: &str = "always";
pub(crate) const COLOR_AUTO: &str = "auto";
pub(crate) const COLOR_NEVER: &str = "never";
pub(crate) const GLOB_ALL: &str = "**";
pub(crate) const OPTION_COLOR: &str = "--color";
pub(crate) const OPTION_HELP: &str = "--help";
pub(crate) const OPTION_HELP_SHORT: &str = "-h";
pub(crate) const OPTION_TARGET: &str = "--target";
pub(crate) const CONFIG_TARGETS_KEY: &str = "targets";
pub(crate) const OWNERSHIP_ROOTS_CONFIG_KEY: &str = "ownership_roots";
pub(crate) const CONFIG_REPOSITORY_RULES_KEY: &str = "repository_rules";
pub(crate) const CONFIG_DUPES_KEY: &str = "dupes";
pub(crate) const CHECK_WARN_ARGUMENT: &str = "--warn";
pub(crate) const CHECK_CACHE_ARGUMENT: &str = "--cache";
pub(crate) const CHECK_NO_CACHE_ARGUMENT: &str = "--no-cache";
pub(crate) const CUSTOM_RULE_TEST_COVERAGE_CODE: &str = "FFR707";
pub(crate) const REPOSITORY_RULE_REQUESTER: &str = ".fensu-repository-rule";
pub(crate) const PROJECT_ROOT_PATH: &str = ".";
pub(crate) const ROLE_HELPERS: &str = "_helpers";
pub(crate) const ROLE_MAIN: &str = "main";
pub(crate) const ROLE_RULES: &str = "rules";
pub(crate) const SCOPE_TEST: &str = "test";
pub(crate) const PROJECT_RULE_REQUESTER: &str = ".fensu-project-rule";
pub(crate) const WEB_ROUTES_DIRECTORY: &str = "routes";
pub(crate) const WEB_SVELTE_EXTENSION: &str = "svelte";
pub(crate) const WEB_PARSE_DIAGNOSTIC_CODE: &str = "FWP001";
pub(crate) const WEB_MODULE_PATH_SEPARATOR: &str = "/";
pub(crate) const RUST_CUSTOM_DEPENDENCY_KINDS: &[&str] = &[
    "tree_paths",
    "tree_files",
    "tree_children",
    "tree_descendants",
    "tree_glob",
    "tree_files_under",
    "tree_position",
    "rust_crates",
    "rust_files",
    "rust_crate",
    "rust_file",
];
pub(crate) const WEB_CUSTOM_DEPENDENCY_KINDS: &[&str] = &[
    "tree_paths",
    "tree_files",
    "tree_children",
    "tree_descendants",
    "tree_glob",
    "tree_files_under",
    "tree_position",
    "web_files",
    "web_file",
    "graph_nodes",
    "graph_node",
    "graph_imports",
    "graph_dependencies",
    "graph_dependents",
    "graph_cycles",
];
pub(crate) const REPOSITORY_CUSTOM_DEPENDENCY_KINDS: &[&str] = &[
    "tree_paths",
    "tree_files",
    "tree_children",
    "tree_descendants",
    "tree_glob",
    "tree_files_under",
    "tree_position",
    "graph_nodes",
    "graph_node",
    "graph_imports",
    "graph_dependencies",
    "graph_dependents",
    "graph_cycles",
    "python_files",
    "python_file",
    "rust_crates",
    "rust_files",
    "rust_crate",
    "rust_file",
    "web_files",
    "web_file",
];
pub(crate) const SCOPE_TOOLING: &str = "tooling";
pub(crate) const STEM_INIT: &str = "__init__";
pub(crate) const SUFFIX_INIT: &str = "__init__.py";
pub(crate) const VALUE_TRUE: &str = "true";
pub(crate) const CONFIG_FENSU_FILE: &str = "fensu.toml";
pub(crate) const CONFIG_PYPROJECT_FILE: &str = "pyproject.toml";
pub(crate) const PYTHON_CACHE_DIRECTORY: &str = "__pycache__";
pub(crate) const CUSTOM_CHECK_TARGETS_ENVIRONMENT_VARIABLE: &str =
    "FENSU_INTERNAL_CUSTOM_CHECK_TARGETS";
pub(crate) const CUSTOM_CHECK_PROTOCOL_VERSION: u32 = 1;
pub(crate) const CURRENT_PATH: &str = ".";
pub(crate) const SCOPE_ROOT: &str = "root";
pub(crate) const MAX_EXPANDED_PATH_PATTERNS: usize = 256;
pub(crate) const MIN_BRACE_ALTERNATIVES: usize = 2;
