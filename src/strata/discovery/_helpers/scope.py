"""Classify Python files under configured roots, tests, and tooling paths."""

from __future__ import annotations

from importlib import import_module
from pathlib import Path
from types import ModuleType

from strata.analysis.constants import NATIVE_FACT_MODULE_NAME
from strata.analysis.main.select_fact_backend import select_fact_backend
from strata.analysis.types import FactBackend
from strata.discovery._helpers.position import relative_parts
from strata.discovery.models import ProjectLayout, ScopedFile
from strata.discovery.types import ScopeName


def discover_scoped_files(*, layout: ProjectLayout) -> tuple[ScopedFile, ...]:
    """Return sorted Python files under configured scan scopes."""

    scope_roots: tuple[tuple[ScopeName, Path], ...] = _configured_scope_roots(layout=layout)
    discovered: dict[Path, ScopedFile] = {}
    for scope, root, walked in _walked_scope_roots(scope_roots=scope_roots):
        for path, canonical, parts in walked:
            resolved_path: Path = canonical if canonical is not None else path.resolve()
            if resolved_path in discovered:
                continue
            discovered[resolved_path] = ScopedFile(
                path=resolved_path,
                root=root,
                scope=scope,
                relative_parts=(
                    tuple(parts)
                    if parts is not None
                    else relative_parts(path=resolved_path, root=root)
                ),
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


def _walked_scope_roots(
    *,
    scope_roots: tuple[tuple[ScopeName, Path], ...],
) -> tuple[
    tuple[ScopeName, Path, tuple[tuple[Path, Path | None, tuple[str, ...] | None], ...]], ...
]:
    directory_roots: tuple[tuple[ScopeName, Path], ...] = tuple(
        (scope, root) for scope, root in scope_roots if root.is_dir()
    )
    native_walked: tuple[tuple[tuple[Path, Path | None, tuple[str, ...] | None], ...], ...] | None
    native_walked = _native_walked(roots=tuple(root for _, root in directory_roots))
    if native_walked is not None:
        return tuple(
            (scope, root, walked)
            for (scope, root), walked in zip(directory_roots, native_walked, strict=True)
        )
    walked_roots: list[tuple[ScopeName, Path, tuple[tuple[Path, Path | None, None], ...]]] = []
    for scope, root in directory_roots:
        entries: tuple[tuple[Path, Path | None, None], ...] = tuple(
            (path, path.resolve(), None) for path in root.rglob("*.py")
        )
        walked_roots.append((scope, root, entries))
    return tuple(walked_roots)


def _native_walked(
    *,
    roots: tuple[Path, ...],
) -> tuple[tuple[tuple[Path, Path | None, tuple[str, ...] | None], ...], ...] | None:
    if select_fact_backend().backend is not FactBackend.NATIVE:
        return None
    try:
        strata_facts: ModuleType = import_module(NATIVE_FACT_MODULE_NAME)
    except ImportError:
        return None
    walked: list[list[tuple[Path, Path | None, list[str] | None]]]
    walked = strata_facts.walk_python_files(list(roots))
    converted: list[tuple[tuple[Path, Path | None, tuple[str, ...] | None], ...]] = []
    for per_root in walked:
        converted.append(
            tuple(
                (path, canonical, tuple(parts) if parts is not None else None)
                for path, canonical, parts in per_root
            )
        )
    return tuple(converted)
