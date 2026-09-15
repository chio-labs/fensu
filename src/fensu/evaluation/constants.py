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
