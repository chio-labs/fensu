"""Constants for call-map discovery and terminal rendering."""

from __future__ import annotations

ANSI_RESET: str = "\x1b[0m"
ANSI_DIM: str = "\x1b[2m"
ANSI_FUNCTION: str = "\x1b[38;5;208m"
ANSI_UNRESOLVED: str = "\x1b[33m"
ANSI_CYCLE: str = "\x1b[35m"
INIT_MODULE_FILE_NAME: str = "__init__.py"
INIT_MODULE_NAME: str = "__init__"
MAX_COMPACT_PATH_PARTS: int = 4
PATH_SYMBOL_SEPARATOR: str = "::"

EXCLUDED_DIRECTORY_NAMES: frozenset[str] = frozenset(
    {
        ".git",
        ".mypy_cache",
        ".nox",
        ".pytest_cache",
        ".ruff_cache",
        ".tox",
        ".venv",
        "__pycache__",
        "build",
        "dist",
        "node_modules",
        "venv",
    }
)
