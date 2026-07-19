"""Safely create canonical source directories for enabled repository memory."""

from __future__ import annotations

import os
import stat
from pathlib import Path

from strata.memory._helpers.native_operations import inspect_sources
from strata.memory.constants import (
    MEMORY_BOOTSTRAP_FILENAME,
    MEMORY_DATABASE_DIRECTORY,
    MEMORY_DIRECTORIES,
    MEMORY_GITIGNORE_ENTRY,
)
from strata.memory.exceptions import MemoryOperationError
from strata.memory.models import MemoryIndexSummary

_GITIGNORE_NAME: str = ".gitignore"
_GITIGNORE_BLOCK: bytes = f"# Strata\n{MEMORY_GITIGNORE_ENTRY}\n".encode()
_FILE_MODE: int = 0o644


def bootstrap_memory(repository_root: Path) -> None:
    """Validate existing sources and create missing canonical Memory state once."""

    marker_path: Path = repository_root / MEMORY_DATABASE_DIRECTORY / MEMORY_BOOTSTRAP_FILENAME
    if marker_path.is_file() and _has_complete_structure(repository_root=repository_root):
        _ensure_gitignore(repository_root=repository_root)
        return
    summary: MemoryIndexSummary = inspect_sources(repository_root)
    diagnostics: int = (
        summary.source_diagnostic_count
        + summary.corpus_diagnostic_count
        + summary.graph_diagnostic_count
    )
    if diagnostics:
        raise MemoryOperationError(
            "Existing .ai content is not canonical and will not be migrated automatically; "
            "migrate it manually before using memory."
        )
    _ensure_gitignore(repository_root=repository_root)
    for relative_path in MEMORY_DIRECTORIES:
        (repository_root / relative_path).mkdir(parents=True, exist_ok=True)
    marker_path.parent.mkdir(parents=True, exist_ok=True)
    marker_path.touch(exist_ok=True)


def _has_complete_structure(*, repository_root: Path) -> bool:
    return all((repository_root / relative_path).is_dir() for relative_path in MEMORY_DIRECTORIES)


def _ensure_gitignore(*, repository_root: Path) -> None:
    path: Path = repository_root / _GITIGNORE_NAME
    flags: int = os.O_RDWR | os.O_APPEND | getattr(os, "O_NOFOLLOW", 0)
    try:
        descriptor: int = os.open(path, flags)
    except FileNotFoundError:
        _create_gitignore(path=path)
        return
    except OSError as error:
        raise MemoryOperationError(f"Memory bootstrap could not open {path}: {error}") from error
    try:
        metadata: os.stat_result = os.fstat(descriptor)
        if not stat.S_ISREG(metadata.st_mode):
            raise MemoryOperationError(
                f"Memory bootstrap requires a regular root gitignore: {path}"
            )
        content: bytes = os.read(descriptor, metadata.st_size)
        if MEMORY_GITIGNORE_ENTRY.encode() in content.splitlines():
            return
        separator: bytes = b"" if not content or content.endswith(b"\n") else b"\n"
        _write_all(descriptor=descriptor, content=separator + _GITIGNORE_BLOCK)
        os.fsync(descriptor)
    except OSError as error:
        raise MemoryOperationError(f"Memory bootstrap could not update {path}: {error}") from error
    finally:
        os.close(descriptor)


def _create_gitignore(*, path: Path) -> None:
    flags: int = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0)
    try:
        descriptor: int = os.open(path, flags, _FILE_MODE)
    except OSError as error:
        raise MemoryOperationError(f"Memory bootstrap could not create {path}: {error}") from error
    try:
        _write_all(descriptor=descriptor, content=_GITIGNORE_BLOCK)
        os.fsync(descriptor)
    except OSError as error:
        raise MemoryOperationError(f"Memory bootstrap could not write {path}: {error}") from error
    finally:
        os.close(descriptor)


def _write_all(*, descriptor: int, content: bytes) -> None:
    remaining: memoryview = memoryview(content)
    while remaining:
        written: int = os.write(descriptor, remaining)
        remaining = remaining[written:]
