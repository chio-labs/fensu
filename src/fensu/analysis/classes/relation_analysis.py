"""Python syntax-relation analysis implementation."""

from __future__ import annotations

from collections.abc import Mapping

from fensu.analysis.exceptions import AnalysisLookupError
from fensu.analysis.models import SyntaxHandle


class PythonRelationAnalysis:
    """Syntax relationships backed by immutable handle indexes."""

    def __init__(
        self,
        *,
        handles: frozenset[SyntaxHandle],
        parent_by_handle: Mapping[SyntaxHandle, SyntaxHandle],
        children_by_handle: Mapping[SyntaxHandle, tuple[SyntaxHandle, ...]],
    ) -> None:
        """Bind known handles and direct syntax relationships."""

        self._handles: frozenset[SyntaxHandle] = handles
        self._parent_by_handle: Mapping[SyntaxHandle, SyntaxHandle] = parent_by_handle
        self._children_by_handle: Mapping[SyntaxHandle, tuple[SyntaxHandle, ...]] = (
            children_by_handle
        )

    def parent(self, handle: SyntaxHandle) -> SyntaxHandle | None:
        """Return the direct parent handle, if present."""

        self._validate_handle(handle)
        return self._parent_by_handle.get(handle)

    def children(self, handle: SyntaxHandle) -> tuple[SyntaxHandle, ...]:
        """Return direct child handles in source traversal order."""

        self._validate_handle(handle)
        return self._children_by_handle.get(handle, ())

    def ancestors(self, handle: SyntaxHandle) -> tuple[SyntaxHandle, ...]:
        """Return parents from nearest to farthest."""

        self._validate_handle(handle)
        result: list[SyntaxHandle] = []
        current: SyntaxHandle | None = self._parent_by_handle.get(handle)
        while current is not None:
            result.append(current)
            current = self._parent_by_handle.get(current)
        return tuple(result)

    def _validate_handle(self, handle: SyntaxHandle) -> None:
        if handle not in self._handles:
            raise AnalysisLookupError(f"Unknown syntax handle {handle}.")
