"""Build backend-neutral locations from Python syntax positions."""

from __future__ import annotations

import ast
from pathlib import Path
from typing import Protocol, cast

from strata.analysis.core.models import SourceLocation, SourcePosition, SourceRange


class _LocatedNode(Protocol):
    lineno: int
    col_offset: int
    end_lineno: int
    end_col_offset: int


def line_offsets(source: str) -> tuple[int, ...]:
    """Return zero-based UTF-8 byte offsets for each source line."""

    offsets: list[int] = [0]
    offset: int = 0
    for line in source.splitlines(keepends=True):
        offset += len(line.encode("utf-8"))
        offsets.append(offset)
    return tuple(offsets)


def source_range(
    *, path: Path, source: str, line_offsets: tuple[int, ...], node: ast.AST
) -> SourceRange:
    """Return the end-exclusive backend-neutral range for one Python AST node."""

    if not hasattr(node, "lineno"):
        return SourceRange(
            path=path,
            start=SourcePosition(line=1, column=0, offset=0),
            end=_source_end(source),
        )
    located_node: _LocatedNode = cast(_LocatedNode, node)
    return SourceRange(
        path=path,
        start=SourcePosition(
            line=located_node.lineno,
            column=located_node.col_offset,
            offset=line_offsets[located_node.lineno - 1] + located_node.col_offset,
        ),
        end=SourcePosition(
            line=located_node.end_lineno,
            column=located_node.end_col_offset,
            offset=line_offsets[located_node.end_lineno - 1] + located_node.end_col_offset,
        ),
    )


def source_location(*, path: Path, node: ast.AST) -> SourceLocation:
    """Return the backend-neutral diagnostic location for one Python AST node."""

    return SourceLocation(
        path=path,
        line=getattr(node, "lineno", 1),
        column=getattr(node, "col_offset", 0),
    )


def _source_end(source: str) -> SourcePosition:
    source_bytes: bytes = source.encode("utf-8")
    last_newline: int = source_bytes.rfind(b"\n")
    column: int = len(source_bytes)
    if last_newline >= 0:
        column = len(source_bytes) - last_newline - 1
    return SourcePosition(
        line=source.count("\n") + 1,
        column=column,
        offset=len(source_bytes),
    )
