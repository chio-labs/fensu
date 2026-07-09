"""Resolve the repository root from explicit config roots."""

from __future__ import annotations

from pathlib import Path

from strata.config.core.models import Config
from strata.discovery.core.exceptions import RepoRootNotFoundError
from strata.discovery.core.models import RepoRoot


def resolve_repo_root(config: Config) -> RepoRoot:
    """Resolve the working repository root and verify configured code roots exist."""

    repo_root: Path = Path.cwd().resolve()
    missing_roots: list[str] = []
    for root in config.roots:
        root_path: Path = _resolve_config_path(repo_root=repo_root, value=root)
        if not root_path.is_dir():
            missing_roots.append(root)
    if missing_roots:
        names: str = ", ".join(sorted(missing_roots))
        raise RepoRootNotFoundError(f"Configured root path(s) do not exist: {names}.")
    return RepoRoot(path=repo_root)


def _resolve_config_path(*, repo_root: Path, value: str) -> Path:
    path: Path = Path(value)
    if path.is_absolute():
        return path.resolve()
    return (repo_root / path).resolve()
