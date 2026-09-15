"""Evaluation runtime constants."""

INIT_MODULE_NAME: str = "__init__"
PREWARM_CHUNK_SIZE: int = 64
PROJECT_REQUESTER_NAME: str = ".fensu-project-rule"
PROJECT_ROOT_PATH: str = "."
PARENT_PATH_PART: str = ".."
ARCHITECTURE_PUBLIC_ROLES: frozenset[str] = frozenset(
    {"main", "classes", "models", "types", "constants", "exceptions"}
)
