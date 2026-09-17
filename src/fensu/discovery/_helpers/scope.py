"""Classify Python files under configured roots, tests, and tooling paths."""

from __future__ import annotations

from importlib import import_module
from pathlib import Path
from types import ModuleType

from fensu.analysis.constants import NATIVE_FACT_MODULE_NAME
from fensu.discovery._helpers.position import normalize_path_spelling, relative_parts
from fensu.discovery.models import OwnershipRoot, ProjectLayout, ScopedFile
from fensu.discovery.types import ScopeName


def discover_scoped_files(*, layout: ProjectLayout) -> tuple[ScopedFile, ...]:
    """Return sorted Python files under configured scan scopes."""

    scope_roots: tuple[tuple[ScopeName, Path], ...] = _configured_scope_roots(layout=layout)
    discovered: dict[Path, ScopedFile] = {}
    for scope, root, walked in _walked_scope_roots(scope_roots=scope_roots):
        resolved_root: Path = normalize_path_spelling(root.resolve())
        for path, canonical, parts in walked:
            if path.is_symlink():
                continue
            resolved_path: Path = normalize_path_spelling(
                canonical if canonical is not None else path.resolve()
            )
            if not resolved_path.is_relative_to(resolved_root):
                continue
            if resolved_path in discovered:
                continue
            relative: tuple[str, ...] = (
                tuple(parts)
                if parts is not None
                else relative_parts(path=resolved_path, root=resolved_root)
            )
            ownership_root, ownership_relative = _ownership_position(
                path=resolved_path,
                relative=relative,
                scope=scope,
                layout=layout,
            )
            discovered[resolved_path] = ScopedFile(
                path=resolved_path,
                root=resolved_root,
                scope=scope,
                relative_parts=relative,
                ownership_root=None if ownership_root is None else ownership_root.path,
                ownership_root_declaration=(
                    None if ownership_root is None else ownership_root.declaration
                ),
                ownership_relative_parts=ownership_relative,
            )
    return tuple(discovered[path] for path in sorted(discovered))


def _ownership_position(
    *,
    path: Path,
    relative: tuple[str, ...],
    scope: ScopeName,
    layout: ProjectLayout,
) -> tuple[OwnershipRoot | None, tuple[str, ...]]:
    if scope is ScopeName.TOOLING:
        return None, relative
    candidate_path: Path = path
    if scope is ScopeName.TEST:
        projected: Path | None = _project_test_path(relative=relative, layout=layout)
        if projected is None:
            return None, relative
        candidate_path = projected
    matches: tuple[OwnershipRoot, ...] = tuple(
        root
        for root in layout.ownership_roots
        if candidate_path == root.path or candidate_path.is_relative_to(root.path)
    )
    if not matches:
        return None, ()
    root: OwnershipRoot = max(matches, key=lambda item: len(item.path.parts))
    return root, candidate_path.relative_to(root.path).parts


def _project_test_path(*, relative: tuple[str, ...], layout: ProjectLayout) -> Path | None:
    directories: tuple[str, ...] = relative[:-1]
    for source in sorted(
        layout.runtime_sources, key=lambda item: len(item.relative_parts), reverse=True
    ):
        width: int = len(source.relative_parts)
        for index in range(len(directories) - width + 1):
            if directories[index : index + width] != source.relative_parts:
                continue
            suffix: tuple[str, ...] = relative[index + width :]
            return source.path.joinpath(*suffix)
    return None


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
    try:
        fensu_facts: ModuleType = import_module(NATIVE_FACT_MODULE_NAME)
    except ImportError:
        return None
    walked: list[list[tuple[Path, Path | None, list[str] | None]]]
    walked = fensu_facts.walk_python_files(list(roots))
    converted: list[tuple[tuple[Path, Path | None, tuple[str, ...] | None], ...]] = []
    for per_root in walked:
        converted.append(
            tuple(
                (path, canonical, tuple(parts) if parts is not None else None)
                for path, canonical, parts in per_root
            )
        )
    return tuple(converted)
