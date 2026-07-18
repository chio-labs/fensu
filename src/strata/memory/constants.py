"""Strata Memory constants."""

from __future__ import annotations

DEFAULT_QUERY_LIMIT: int = 20
MAX_QUERY_LIMIT: int = 1000
DEFAULT_GRAPH_DEPTH: int = 2
DEFAULT_GRAPH_MAX_NODES: int = 50
DEFAULT_GRAPH_MAX_EDGES: int = 100
MIN_GRAPH_DEPTH: int = 1
MAX_GRAPH_DEPTH: int = 5
MIN_GRAPH_NODES: int = 1
MAX_GRAPH_NODES: int = 200
MIN_GRAPH_EDGES: int = 1
MAX_GRAPH_EDGES: int = 500
MEMORY_DATABASE_DIRECTORY: str = ".strata/memory"
MEMORY_DATABASE_FILENAME: str = "memory.sqlite3"
MEMORY_BOOTSTRAP_FILENAME: str = ".bootstrapped"
MEMORY_GITIGNORE_ENTRY: str = ".strata/memory/"
MEMORY_DIRECTORIES: tuple[str, ...] = (
    ".ai/tasks/not-started",
    ".ai/tasks/in-progress",
    ".ai/tasks/completed",
    ".ai/tasks/cancelled",
    ".ai/tasks/superseded",
    ".ai/knowledge/repo/notes",
    ".ai/knowledge/repo/decisions",
    ".ai/knowledge/repo/skills",
    ".ai/_archive/tasks/completed",
    ".ai/_archive/tasks/cancelled",
    ".ai/_archive/tasks/superseded",
    ".ai/_archive/knowledge/repo/notes",
    ".ai/_archive/knowledge/repo/decisions",
    ".ai/_archive/knowledge/repo/skills",
)
MEMORY_SCHEMA_PREFIX: str = "memory."
NULL_TEXT: str = "NULL"
RELATION_KIND_TABLE: str = "table"
RELATION_KIND_VIEW: str = "view"
ANSI_BOLD_CYAN: str = "\x1b[1;36m"
ANSI_RESET: str = "\x1b[0m"
ARCHIVE_STATE_ARCHIVED: str = "archived"
RESOLUTION_STATUS_RESOLVED: str = "resolved"
