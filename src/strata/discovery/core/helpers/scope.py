"""Classify Python files under configured roots, tests, and tooling paths."""

from __future__ import annotations

from pathlib import Path

from strata.discovery.core.helpers.position import relative_parts
from strata.discovery.core.models import ProjectLayout, ScopedFile
from strata.discovery.core.types import ScopeName


def discover_scoped_files(*, layout: ProjectLayout) -> tuple[ScopedFile, ...]:
    """Return sorted Python files under configured scan scopes."""

    scope_roots: tuple[tuple[ScopeName, Path], ...] = _configured_scope_roots(layout=layout)
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


def _configured_scope_roots(*, layout: ProjectLayout) -> tuple[tuple[ScopeName, Path], ...]:
    root_scopes: tuple[tuple[ScopeName, Path], ...] = tuple(
        (ScopeName.ROOT, source.path) for source in layout.runtime_sources
    )
    test_scopes: tuple[tuple[ScopeName, Path], ...] = tuple(
        (ScopeName.TEST, root.path) for root in layout.test_roots
    )
    tooling_scopes: tuple[tuple[ScopeName, Path], ...] = tuple(
        (ScopeName.TOOLING, source.path) for source in layout.tooling_sources
    )
    return tuple(
        sorted(
            (*root_scopes, *test_scopes, *tooling_scopes),
            key=lambda item: len(item[1].parts),
            reverse=True,
        )
    )
