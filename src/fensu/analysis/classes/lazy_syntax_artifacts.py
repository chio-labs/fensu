"""Lazily parsed CPython syntax artifacts shared by one file's consumers."""

from __future__ import annotations

import ast
from collections.abc import Mapping
from pathlib import Path

from fensu.analysis._helpers.building import index_module_nodes
from fensu.analysis.types import SyntaxIndexes
from fensu.instrumentation.constants import OPERATION_COUNTERS, PARSE_OPERATION


class LazySyntaxArtifacts:
    """CPython module and traversal indexes constructed on first demand."""

    def __init__(self, *, path: Path, source: str, module: ast.Module | None = None) -> None:
        """Bind one decoded source identity, optionally adopting an eager module."""

        self._path: Path = path
        self._source: str = source
        self._module: ast.Module | None = module
        self._indexes: SyntaxIndexes | None = None

    @property
    def module(self) -> ast.Module:
        """Return the CPython module, parsing the bound source on first access."""

        if self._module is None:
            OPERATION_COUNTERS.record(operation=PARSE_OPERATION)
            self._module = ast.parse(self._source, filename=str(self._path))
        return self._module

    @property
    def nodes(self) -> tuple[ast.AST, ...]:
        """Return every node in breadth-first traversal order."""

        return self._ensure_indexes().nodes

    @property
    def node_index(self) -> Mapping[type[ast.AST], tuple[ast.AST, ...]]:
        """Return traversal-ordered nodes grouped by node type."""

        return self._ensure_indexes().node_index

    @property
    def parent_by_node(self) -> Mapping[ast.AST, ast.AST]:
        """Return the parent of every non-module node."""

        return self._ensure_indexes().parent_by_node

    def _ensure_indexes(self) -> SyntaxIndexes:
        if self._indexes is None:
            self._indexes = index_module_nodes(module=self.module)
        return self._indexes
