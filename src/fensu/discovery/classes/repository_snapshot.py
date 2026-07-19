"""Process-wide canonical path and content-hash table seeded by discovery."""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path

_WINDOWS_PATH_SEPARATOR: str = "\\"


class RepositorySnapshot:
    """Canonical repository file identities captured during one discovery pass."""

    def __init__(self) -> None:
        self._repo_root: str | None = None
        self._relative_by_path: dict[str, str] = {}
        self._hash_by_path: dict[str, str] = {}

    def install(self, *, repo_root: Path, relative_by_path: Mapping[str, str]) -> None:
        """Replace the table with validated canonical-to-relative path identities."""

        installed: dict[str, str] = {}
        for path, relative in relative_by_path.items():
            if _WINDOWS_PATH_SEPARATOR in relative:
                continue
            installed[path] = relative
        self._repo_root = str(repo_root)
        self._relative_by_path = installed
        self._hash_by_path = {}

    def clear(self) -> None:
        """Forget every installed path and hash."""

        self._repo_root = None
        self._relative_by_path = {}
        self._hash_by_path = {}

    def relative_path(self, *, path: Path, repo_root: Path) -> str | None:
        """Return the known repository-relative POSIX spelling, if installed."""

        if self._repo_root is None or self._repo_root != str(repo_root):
            return None
        return self._relative_by_path.get(str(path))

    def seed_hashes(self, *, hash_by_path: Mapping[str, str]) -> None:
        """Record content hashes for installed canonical path spellings."""

        self._hash_by_path = dict(hash_by_path)

    def source_hash(self, *, path: Path) -> str | None:
        """Return the seeded content hash for one canonical path, if known."""

        return self._hash_by_path.get(str(path))

    def installed_paths(self) -> tuple[str, ...]:
        """Return every installed canonical path spelling."""

        return tuple(self._relative_by_path)
