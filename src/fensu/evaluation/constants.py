"""Evaluation runtime constants."""

INIT_MODULE_NAME: str = "__init__"
PREWARM_CHUNK_SIZE: int = 64
PROJECT_REQUESTER_NAME: str = ".fensu-project-rule"
PROJECT_ROOT_PATH: str = "."
PARENT_PATH_PART: str = ".."
ARCHITECTURE_PUBLIC_ROLES: frozenset[str] = frozenset(
    {"main", "classes", "models", "types", "constants", "exceptions"}
)
RUST_CUSTOM_CACHE_SCHEMA: int = 1
RUST_CUSTOM_CACHE_RELATIVE_PATH: str = ".fensu/cache/rust-custom-v1.json"
RUST_CUSTOM_CACHE_RECORD_FIELDS: frozenset[str] = frozenset({"dependencies", "findings"})
RUST_CUSTOM_DEPENDENCY_FIELDS: frozenset[str] = frozenset({"requester", "kind", "query", "answer"})
RUST_CUSTOM_FINDING_FIELDS: frozenset[str] = frozenset(
    {"code", "path", "line", "column", "symbol", "message", "remediation", "severity"}
)
RUST_CUSTOM_FINDING_SEVERITIES: frozenset[str] = frozenset({"blocking", "warning"})
RUST_DEPENDENCY_TREE_PATHS: str = "tree_paths"
RUST_DEPENDENCY_TREE_FILES: str = "tree_files"
RUST_DEPENDENCY_TREE_CHILDREN: str = "tree_children"
RUST_DEPENDENCY_TREE_DESCENDANTS: str = "tree_descendants"
RUST_DEPENDENCY_TREE_GLOB: str = "tree_glob"
RUST_DEPENDENCY_TREE_FILES_UNDER: str = "tree_files_under"
RUST_DEPENDENCY_TREE_POSITION: str = "tree_position"
RUST_DEPENDENCY_CRATES: str = "rust_crates"
RUST_DEPENDENCY_FILES: str = "rust_files"
RUST_DEPENDENCY_CRATE: str = "rust_crate"
RUST_DEPENDENCY_FILE: str = "rust_file"
WEB_CUSTOM_CACHE_SCHEMA: int = 1
WEB_CUSTOM_CACHE_RELATIVE_PATH: str = ".fensu/cache/web-custom-v1.json"
REPOSITORY_CUSTOM_CACHE_SCHEMA: str = "repository-custom-v3"
REPOSITORY_CUSTOM_CACHE_RELATIVE_PATH: str = ".fensu/cache/repository-custom-v3.json"
REPOSITORY_FACT_SCHEMA_VERSION: str = "repository-facts-v1"
REPOSITORY_RULE_CACHE_CONTRACT_VERSION: str = "repository-rules-v3"
PYTHON_REPOSITORY_FACT_SCHEMA_VERSION: str = "python-repository-facts-v3"
MINIMUM_REPOSITORY_TARGETS: int = 2
REPOSITORY_RULE_REQUESTER: str = ".fensu-repository-rule"
REPOSITORY_CACHE_RECORD_FIELDS: frozenset[str] = frozenset({"findings", "dependencies"})
REPOSITORY_DEPENDENCY_FIELDS: frozenset[str] = frozenset(
    {"requester", "target", "kind", "query", "answer"}
)
REPOSITORY_FINDING_FIELDS: frozenset[str] = frozenset(
    {"code", "path", "line", "column", "symbol", "message", "remediation", "severity"}
)
REPOSITORY_FINDING_SEVERITIES: frozenset[str] = frozenset({"blocking", "warning"})
REPOSITORY_TARGET_PAYLOAD_FIELDS: frozenset[str] = frozenset(
    {"name", "analyzer", "root", "ownership_roots", "facts", "subjects"}
)
PYTHON_REPOSITORY_FACT_FIELDS: frozenset[str] = frozenset(
    {"schema_version", "parser_contract", "files"}
)
WEB_CUSTOM_CACHE_RECORD_FIELDS: frozenset[str] = RUST_CUSTOM_CACHE_RECORD_FIELDS
WEB_CUSTOM_DEPENDENCY_FIELDS: frozenset[str] = RUST_CUSTOM_DEPENDENCY_FIELDS
WEB_CUSTOM_FINDING_FIELDS: frozenset[str] = RUST_CUSTOM_FINDING_FIELDS
WEB_CUSTOM_FINDING_SEVERITIES: frozenset[str] = RUST_CUSTOM_FINDING_SEVERITIES
WEB_DEPENDENCY_TREE_PATHS: str = RUST_DEPENDENCY_TREE_PATHS
WEB_DEPENDENCY_TREE_FILES: str = RUST_DEPENDENCY_TREE_FILES
WEB_DEPENDENCY_TREE_CHILDREN: str = RUST_DEPENDENCY_TREE_CHILDREN
WEB_DEPENDENCY_TREE_DESCENDANTS: str = RUST_DEPENDENCY_TREE_DESCENDANTS
WEB_DEPENDENCY_TREE_GLOB: str = RUST_DEPENDENCY_TREE_GLOB
WEB_DEPENDENCY_TREE_FILES_UNDER: str = RUST_DEPENDENCY_TREE_FILES_UNDER
WEB_DEPENDENCY_TREE_POSITION: str = RUST_DEPENDENCY_TREE_POSITION
WEB_DEPENDENCY_FILES: str = "web_files"
WEB_DEPENDENCY_FILE: str = "web_file"
WEB_GRAPH_NODES: str = "graph_nodes"
WEB_GRAPH_NODE: str = "graph_node"
WEB_GRAPH_IMPORTS: str = "graph_imports"
WEB_GRAPH_DEPENDENCIES: str = "graph_dependencies"
WEB_GRAPH_DEPENDENTS: str = "graph_dependents"
WEB_GRAPH_CYCLES: str = "graph_cycles"
