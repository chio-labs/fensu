"""Answer project dependency queries identically at record and replay time."""

from __future__ import annotations

import hashlib
from pathlib import Path

from strata.instrumentation.constants import (
    OPERATION_COUNTERS,
    PROJECT_QUERY_ANSWER_ITEM_OPERATION,
    PROJECT_QUERY_DIRECTORY_ENTRIES_OPERATION,
    PROJECT_QUERY_EXISTS_OPERATION,
    PROJECT_QUERY_GLOB_OPERATION,
    PROJECT_QUERY_IS_DIR_OPERATION,
    PROJECT_QUERY_IS_FILE_OPERATION,
    PROJECT_QUERY_OBSERVATION_OPERATION,
    PROJECT_QUERY_PYTHON_ANCHOR_OPERATION,
    PROJECT_QUERY_SOURCE_OPERATION,
)


class QueryObserver:
    """Single owner of dependency-query semantics shared by evaluation and cache."""

    def source_fingerprint(self, *, path: Path) -> str | None:
        """Return the SHA-256 identity of the path's bytes or None when unreadable."""

        OPERATION_COUNTERS.record(operation=PROJECT_QUERY_OBSERVATION_OPERATION)
        OPERATION_COUNTERS.record(operation=PROJECT_QUERY_SOURCE_OPERATION)
        try:
            content: bytes = path.read_bytes()
        except OSError:
            return None
        OPERATION_COUNTERS.record(operation=PROJECT_QUERY_ANSWER_ITEM_OPERATION)
        return hashlib.sha256(content).hexdigest()

    def exists(self, *, resolved_path: Path) -> bool:
        """Return whether a resolved path exists."""

        OPERATION_COUNTERS.record(operation=PROJECT_QUERY_OBSERVATION_OPERATION)
        OPERATION_COUNTERS.record(operation=PROJECT_QUERY_EXISTS_OPERATION)
        OPERATION_COUNTERS.record(operation=PROJECT_QUERY_ANSWER_ITEM_OPERATION)
        return resolved_path.exists()

    def is_file(self, *, resolved_path: Path) -> bool:
        """Return whether a resolved path is a regular file."""

        OPERATION_COUNTERS.record(operation=PROJECT_QUERY_OBSERVATION_OPERATION)
        OPERATION_COUNTERS.record(operation=PROJECT_QUERY_IS_FILE_OPERATION)
        OPERATION_COUNTERS.record(operation=PROJECT_QUERY_ANSWER_ITEM_OPERATION)
        return resolved_path.is_file()

    def is_dir(self, *, resolved_path: Path) -> bool:
        """Return whether a resolved path is a directory."""

        OPERATION_COUNTERS.record(operation=PROJECT_QUERY_OBSERVATION_OPERATION)
        OPERATION_COUNTERS.record(operation=PROJECT_QUERY_IS_DIR_OPERATION)
        OPERATION_COUNTERS.record(operation=PROJECT_QUERY_ANSWER_ITEM_OPERATION)
        return resolved_path.is_dir()

    def directory_entries(self, *, query_path: Path) -> tuple[Path, ...]:
        """Return the direct children of a directory in observation order."""

        OPERATION_COUNTERS.record(operation=PROJECT_QUERY_OBSERVATION_OPERATION)
        OPERATION_COUNTERS.record(operation=PROJECT_QUERY_DIRECTORY_ENTRIES_OPERATION)
        entries: tuple[Path, ...] = tuple(query_path.iterdir())
        OPERATION_COUNTERS.record(
            operation=PROJECT_QUERY_ANSWER_ITEM_OPERATION,
            amount=len(entries),
        )
        return entries

    def glob(self, *, query_path: Path, pattern: str, recursive: bool) -> tuple[Path, ...]:
        """Return direct or recursive pattern matches in observation order."""

        OPERATION_COUNTERS.record(operation=PROJECT_QUERY_OBSERVATION_OPERATION)
        OPERATION_COUNTERS.record(operation=PROJECT_QUERY_GLOB_OPERATION)
        matches: tuple[Path, ...] = tuple(
            query_path.rglob(pattern) if recursive else query_path.glob(pattern)
        )
        OPERATION_COUNTERS.record(
            operation=PROJECT_QUERY_ANSWER_ITEM_OPERATION,
            amount=len(matches),
        )
        return matches

    def python_anchor(self, *, query_path: Path) -> Path | None:
        """Return init, first direct module, or first descendant module in that order."""

        OPERATION_COUNTERS.record(operation=PROJECT_QUERY_OBSERVATION_OPERATION)
        OPERATION_COUNTERS.record(operation=PROJECT_QUERY_PYTHON_ANCHOR_OPERATION)
        init_path: Path = query_path / "__init__.py"
        if init_path.is_file():
            OPERATION_COUNTERS.record(operation=PROJECT_QUERY_ANSWER_ITEM_OPERATION)
            return init_path
        direct_modules: tuple[Path, ...] = tuple(sorted(query_path.glob("*.py")))
        if direct_modules:
            OPERATION_COUNTERS.record(operation=PROJECT_QUERY_ANSWER_ITEM_OPERATION)
            return direct_modules[0]
        descendant_modules: tuple[Path, ...] = tuple(sorted(query_path.rglob("*.py")))
        if not descendant_modules:
            return None
        OPERATION_COUNTERS.record(operation=PROJECT_QUERY_ANSWER_ITEM_OPERATION)
        return descendant_modules[0]
