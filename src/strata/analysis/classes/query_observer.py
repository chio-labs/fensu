"""Answer project dependency queries identically at record and replay time."""

from __future__ import annotations

import hashlib
from pathlib import Path


class QueryObserver:
    """Single owner of dependency-query semantics shared by evaluation and cache."""

    def source_fingerprint(self, *, path: Path) -> str | None:
        """Return the SHA-256 identity of the path's bytes or None when unreadable."""

        try:
            content: bytes = path.read_bytes()
        except OSError:
            return None
        return hashlib.sha256(content).hexdigest()

    def exists(self, *, resolved_path: Path) -> bool:
        """Return whether a resolved path exists."""

        return resolved_path.exists()

    def is_file(self, *, resolved_path: Path) -> bool:
        """Return whether a resolved path is a regular file."""

        return resolved_path.is_file()

    def is_dir(self, *, resolved_path: Path) -> bool:
        """Return whether a resolved path is a directory."""

        return resolved_path.is_dir()

    def directory_entries(self, *, query_path: Path) -> tuple[Path, ...]:
        """Return the direct children of a directory in observation order."""

        return tuple(query_path.iterdir())

    def glob(self, *, query_path: Path, pattern: str, recursive: bool) -> tuple[Path, ...]:
        """Return direct or recursive pattern matches in observation order."""

        return tuple(query_path.rglob(pattern) if recursive else query_path.glob(pattern))

    def python_anchor(self, *, query_path: Path) -> Path | None:
        """Return init, first direct module, or first descendant module in that order."""

        init_path: Path = query_path / "__init__.py"
        if init_path.is_file():
            return init_path
        direct_modules: tuple[Path, ...] = tuple(sorted(query_path.glob("*.py")))
        if direct_modules:
            return direct_modules[0]
        descendant_modules: tuple[Path, ...] = tuple(sorted(query_path.rglob("*.py")))
        return descendant_modules[0] if descendant_modules else None
