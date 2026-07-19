"""Persistent call-map cache models."""

from __future__ import annotations

from dataclasses import dataclass

from fensu.mapping.models import CallMapNode


@dataclass(frozen=True, slots=True)
class MappingIdentity:
    """Process-independent implementation inputs shared by all map records."""

    contract: int
    python_implementation: str
    python_version: str
    fensu_implementation: str


@dataclass(frozen=True, slots=True)
class FunctionDeclaration:
    """Canonical function selection metadata for one source file."""

    key: str
    name: str
    qualified_name: str
    owning_class: str | None


@dataclass(frozen=True, slots=True)
class ClassDeclaration:
    """Canonical nominal inheritance metadata for one project class."""

    key: str
    base_keys: tuple[str, ...]
    protocol: bool


@dataclass(frozen=True, slots=True)
class FileDeclarations:
    """Strict persisted declaration metadata for one source identity."""

    identity: str
    path: str
    module_name: str
    functions: tuple[FunctionDeclaration, ...]
    classes: tuple[ClassDeclaration, ...]
    record_fingerprint: str = ""


@dataclass(frozen=True, slots=True)
class MapManifest:
    """Exact project generation and point-lookup tables."""

    input_fingerprint: str
    files: tuple[FileDeclarations, ...]
    functions: dict[str, str]
    classes: dict[str, str]
    bare_functions: dict[str, tuple[str, ...]]
    protocol_implementations: dict[str, tuple[str, ...]]
    record_fingerprint: str = ""


@dataclass(frozen=True, slots=True)
class MapCacheStats:
    """Observable mapping-cache work for one invocation."""

    manifest_hit: bool = False
    parsed_files: int = 0
    reused_file_records: int = 0
    writes: int = 0
    storage_failed: bool = False
    internal_error: bool = False


@dataclass(frozen=True, slots=True)
class CachedCallMap:
    """One call tree and its mapping-cache operation counts."""

    root: CallMapNode
    stats: MapCacheStats
