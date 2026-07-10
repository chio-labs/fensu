"""Private backend-neutral source-analysis contracts."""

from __future__ import annotations

import ast
from collections.abc import Mapping
from typing import NamedTuple, Protocol

from strata.analysis.core.models import OuterStateMutationFact, SourceRange, SyntaxHandle


class TextAnalysis(Protocol):
    """Source text queries using backend-neutral locations."""

    @property
    def source(self) -> str:
        """Return the complete source text."""
        ...

    def line(self, line_number: int) -> str:
        """Return one source line without its line ending."""
        ...

    def slice(self, source_range: SourceRange) -> str:
        """Return the text covered by an end-exclusive source range."""
        ...


class SyntaxAnalysis(Protocol):
    """Backend-neutral syntax identity, kind, and location queries."""

    def handles(self, *, kind: str | None = None) -> tuple[SyntaxHandle, ...]:
        """Return syntax handles in deterministic traversal order."""
        ...

    def kind(self, handle: SyntaxHandle) -> str:
        """Return the Strata syntax kind for a handle."""
        ...

    def range(self, handle: SyntaxHandle) -> SourceRange:
        """Return the source range for a handle."""
        ...


class RelationAnalysis(Protocol):
    """Backend-neutral syntax relationship queries."""

    def parent(self, handle: SyntaxHandle) -> SyntaxHandle | None:
        """Return the direct parent handle, if present."""
        ...

    def children(self, handle: SyntaxHandle) -> tuple[SyntaxHandle, ...]:
        """Return direct child handles in source traversal order."""
        ...

    def ancestors(self, handle: SyntaxHandle) -> tuple[SyntaxHandle, ...]:
        """Return parents from nearest to farthest."""
        ...


class FactAnalysis(Protocol):
    """Backend-neutral semantic facts computed for the current file."""

    def outer_state_mutations(self) -> tuple[OuterStateMutationFact, ...]:
        """Return direct mutations resolving to state owned by an outer scope."""
        ...


class Analysis(Protocol):
    """Private replaceable analysis facade attached to a rule context."""

    @property
    def text(self) -> TextAnalysis:
        """Return source-text queries."""
        ...

    @property
    def syntax(self) -> SyntaxAnalysis:
        """Return syntax queries."""
        ...

    @property
    def relations(self) -> RelationAnalysis:
        """Return syntax-relation queries."""
        ...

    @property
    def facts(self) -> FactAnalysis:
        """Return semantic file facts."""
        ...


class AnalysisBuild(NamedTuple):
    """One analysis facade plus compatibility indexes from the same traversal."""

    analysis: Analysis
    node_index: Mapping[type[ast.AST], tuple[ast.AST, ...]]
    parent_by_node: Mapping[ast.AST, ast.AST]
