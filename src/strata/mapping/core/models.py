"""Call-map models."""

from __future__ import annotations

import ast
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class MappingSource:
    """A directory to scan and the import root used to name its modules."""

    scan_path: Path
    import_root: Path


@dataclass(frozen=True, slots=True)
class MappingProject:
    """Repository display root and Python sources included in one map."""

    repo_root: Path
    sources: tuple[MappingSource, ...]


@dataclass(frozen=True, slots=True)
class FunctionDefinition:
    """A project-owned top-level function definition."""

    module_name: str
    name: str
    path: Path
    node: ast.FunctionDef | ast.AsyncFunctionDef
    imported_symbols: dict[str, tuple[str, str]]
    imported_modules: dict[str, str]


@dataclass(frozen=True, slots=True)
class UnresolvedCall:
    """A dynamic call seam that the active provider cannot resolve."""

    name: str
    line: int
    reason: str


@dataclass(frozen=True, slots=True)
class CallMapNode:
    """One function and its resolved project-local callees."""

    definition: FunctionDefinition
    entries: tuple[CallMapNode | UnresolvedCall, ...]
    cycle: bool = False
    truncated: bool = False
