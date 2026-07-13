"""Python file-analysis facade."""

from __future__ import annotations

import ast
from collections.abc import Mapping
from pathlib import Path
from typing import cast

from strata.analysis._helpers.locations import line_offsets, source_range
from strata.analysis.classes.fact_analysis import PythonFactAnalysis
from strata.analysis.classes.relation_analysis import PythonRelationAnalysis
from strata.analysis.classes.syntax_analysis import PythonSyntaxAnalysis
from strata.analysis.classes.text_analysis import PythonTextAnalysis
from strata.analysis.models import NodeId, SourceRange, SyntaxHandle
from strata.analysis.types import FactAnalysis, RelationAnalysis, SyntaxAnalysis, TextAnalysis


class PythonFileAnalysis:
    """Private analysis facade composed from Python-backed query zones."""

    def __init__(
        self,
        *,
        path: Path,
        source: str,
        nodes: tuple[ast.AST, ...],
        node_index: Mapping[type[ast.AST], tuple[ast.AST, ...]],
        parent_by_node: Mapping[ast.AST, ast.AST],
    ) -> None:
        """Bind indexed syntax and defer backend-neutral object materialization."""

        self._path: Path = path
        self._source: str = source
        self._nodes: tuple[ast.AST, ...] = nodes
        self._node_index: Mapping[type[ast.AST], tuple[ast.AST, ...]] = node_index
        self._parent_by_node: Mapping[ast.AST, ast.AST] = parent_by_node
        self._text: TextAnalysis | None = None
        self._syntax: SyntaxAnalysis | None = None
        self._relations: RelationAnalysis | None = None
        self._facts: FactAnalysis | None = None

    @property
    def facts(self) -> FactAnalysis:
        """Return semantic file facts."""

        if self._facts is None:
            module: ast.Module = cast(ast.Module, self._nodes[0])
            self._facts = PythonFactAnalysis(
                path=self._path,
                source=self._source,
                module=module,
                nodes=self._nodes,
                node_index=self._node_index,
                parent_by_node=self._parent_by_node,
            )
        return self._facts

    @property
    def text(self) -> TextAnalysis:
        """Return source-text queries."""

        self._ensure_queries()
        return cast(TextAnalysis, self._text)

    @property
    def syntax(self) -> SyntaxAnalysis:
        """Return syntax queries."""

        self._ensure_queries()
        return cast(SyntaxAnalysis, self._syntax)

    @property
    def relations(self) -> RelationAnalysis:
        """Return syntax-relation queries."""

        self._ensure_queries()
        return cast(RelationAnalysis, self._relations)

    def _ensure_queries(self) -> None:
        if self._syntax is not None:
            return
        handle_by_node: dict[ast.AST, SyntaxHandle] = {
            node: SyntaxHandle(path=self._path, node_id=NodeId(index))
            for index, node in enumerate(self._nodes)
        }
        handles: tuple[SyntaxHandle, ...] = tuple(handle_by_node[node] for node in self._nodes)
        parent_by_handle: dict[SyntaxHandle, SyntaxHandle] = {
            handle_by_node[node]: handle_by_node[parent]
            for node, parent in self._parent_by_node.items()
        }
        child_handles_by_node: dict[ast.AST, list[SyntaxHandle]] = {
            node: [] for node in self._nodes
        }
        for child, parent in self._parent_by_node.items():
            child_handles_by_node[parent].append(handle_by_node[child])
        children_by_handle: dict[SyntaxHandle, tuple[SyntaxHandle, ...]] = {
            handle_by_node[node]: tuple(child_handles_by_node[node]) for node in self._nodes
        }
        offsets: tuple[int, ...] = line_offsets(self._source)
        range_by_handle: dict[SyntaxHandle, SourceRange] = {
            handle_by_node[node]: source_range(
                path=self._path,
                source=self._source,
                line_offsets=offsets,
                node=node,
            )
            for node in self._nodes
        }
        self._text = PythonTextAnalysis(path=self._path, source=self._source)
        self._syntax = PythonSyntaxAnalysis(
            handles=handles,
            kind_by_handle={handle_by_node[node]: type(node).__name__ for node in self._nodes},
            range_by_handle=range_by_handle,
        )
        self._relations = PythonRelationAnalysis(
            handles=frozenset(handles),
            parent_by_handle=parent_by_handle,
            children_by_handle=children_by_handle,
        )
