"""Discover immutable mapping sources through the native repository index."""

from __future__ import annotations

from importlib import import_module
from pathlib import Path
from types import ModuleType

from fensu.analysis.constants import NATIVE_FACT_MODULE_NAME
from fensu.cache.fingerprints.main.source import fingerprint_source
from fensu.mapping.constants import (
    EXCLUDED_DIRECTORY_NAMES,
    INIT_MODULE_NAME,
    PYTHON_SOURCE_SUFFIX,
)
from fensu.mapping.models import MappingSource, SourceSnapshot


def discover_source_snapshots(
    *, sources: tuple[MappingSource, ...], repo_root: Path | None
) -> tuple[SourceSnapshot, ...]:
    """Read every native-discovered Python source exactly once."""

    native: ModuleType = import_module(NATIVE_FACT_MODULE_NAME)
    walked: list[list[tuple[Path, Path | None, list[str] | None]]]
    walked = native.walk_python_files([source.scan_path for source in sources])
    discovered: dict[Path, Path] = {}
    for mapping_source, entries in zip(sources, walked, strict=True):
        for entry_path, canonical_path, relative_parts in entries:
            if (
                canonical_path is None
                or relative_parts is None
                or entry_path.suffix != PYTHON_SOURCE_SUFFIX
            ):
                continue
            if any(part in EXCLUDED_DIRECTORY_NAMES for part in relative_parts):
                continue
            discovered.setdefault(canonical_path, mapping_source.import_root)
    snapshots: list[SourceSnapshot] = []
    for path in sorted(discovered):
        import_root: Path = discovered[path]
        source: bytes = path.read_bytes()
        snapshots.append(
            SourceSnapshot(
                path=path,
                relative_path=_cache_safe_path(path=path, repo_root=repo_root),
                import_root=import_root,
                import_root_identity=_cache_safe_path(path=import_root, repo_root=repo_root),
                module_name=_module_name(path=path, import_root=import_root),
                source=source,
                source_fingerprint=fingerprint_source(source).value,
            )
        )
    return tuple(snapshots)


def _module_name(*, path: Path, import_root: Path) -> str:
    parts: tuple[str, ...] = path.relative_to(import_root).parts
    module_parts: tuple[str, ...] = (*parts[:-1], parts[-1].removesuffix(".py"))
    if module_parts[-1] == INIT_MODULE_NAME:
        module_parts = module_parts[:-1]
    return ".".join(module_parts)


def _cache_safe_path(*, path: Path, repo_root: Path | None) -> str:
    if repo_root is not None and path.is_relative_to(repo_root):
        return path.relative_to(repo_root).as_posix()
    return path.as_posix()
