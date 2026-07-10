"""Classify Python files under configured roots, tests, and tooling paths."""

from __future__ import annotations

from pathlib import Path

from strata.config.core.models import Config
from strata.discovery.core.helpers.position import relative_parts
from strata.discovery.core.models import RepoRoot, ScopedFile
from strata.discovery.core.types import ScopeName


def discover_scoped_files(*, config: Config, repo_root: RepoRoot) -> tuple[ScopedFile, ...]:
    """Return sorted Python files under configured scan scopes."""

    scope_roots: tuple[tuple[ScopeName, Path], ...] = _configured_scope_roots(
        config=config, repo_root=repo_root
    )
    discovered: dict[Path, ScopedFile] = {}
    for scope, root in scope_roots:
        if not root.is_dir():
            continue
        for path in root.rglob("*.py"):
            resolved_path: Path = path.resolve()
            if resolved_path in discovered:
                continue
            discovered[resolved_path] = ScopedFile(
                path=resolved_path,
                root=root,
                scope=scope,
                relative_parts=relative_parts(path=resolved_path, root=root),
            )
    return tuple(discovered[path] for path in sorted(discovered))


def _configured_scope_roots(
    *, config: Config, repo_root: RepoRoot
) -> tuple[tuple[ScopeName, Path], ...]:
    root_scopes: tuple[tuple[ScopeName, Path], ...] = tuple(
        (ScopeName.ROOT, _resolve_path(repo_root=repo_root, value=root)) for root in config.roots
    )
    test_scopes: tuple[tuple[ScopeName, Path], ...] = tuple(
        (ScopeName.TEST, _resolve_path(repo_root=repo_root, value=root)) for root in config.tests
    )
    tooling_scopes: tuple[tuple[ScopeName, Path], ...] = tuple(
        (ScopeName.TOOLING, _resolve_path(repo_root=repo_root, value=root))
        for root in config.tooling
    )
    return (*root_scopes, *test_scopes, *tooling_scopes)


def _resolve_path(*, repo_root: RepoRoot, value: str) -> Path:
    path: Path = Path(value)
    if path.is_absolute():
        return path.resolve()
    return (repo_root.path / path).resolve()
