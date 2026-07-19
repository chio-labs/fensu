"""Resolve the repository root from explicit config roots."""

from __future__ import annotations

from pathlib import Path

from fensu.discovery.models import RepoRoot


def resolve_repo_root(*, path: Path | None = None) -> RepoRoot:
    """Resolve the explicit or working repository root."""

    return RepoRoot(path=(Path.cwd() if path is None else path).resolve())
