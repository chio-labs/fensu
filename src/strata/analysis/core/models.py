"""Backend-neutral source identity and location models."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class NodeId:
    """An opaque syntax identity unique within one analyzed file."""

    value: int


@dataclass(frozen=True, slots=True)
class SyntaxHandle:
    """A file-qualified opaque reference to one syntax node."""

    path: Path
    node_id: NodeId


@dataclass(frozen=True, slots=True, order=True)
class SourcePosition:
    """A one-based line and zero-based UTF-8 byte column and offset."""

    line: int
    column: int
    offset: int


@dataclass(frozen=True, slots=True)
class SourceRange:
    """An end-exclusive source range within one file."""

    path: Path
    start: SourcePosition
    end: SourcePosition


@dataclass(frozen=True, slots=True)
class OuterStateMutationFact:
    """A direct mutation resolving to module or enclosing-function state."""

    location: SourceRange
