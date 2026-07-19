"""Python syntax analysis implementation."""

from __future__ import annotations

from collections.abc import Mapping

from fensu.analysis.exceptions import AnalysisLookupError
from fensu.analysis.models import SourceRange, SyntaxHandle


class PythonSyntaxAnalysis:
    """Syntax queries backed by precomputed immutable facts."""

    def __init__(
        self,
        *,
        handles: tuple[SyntaxHandle, ...],
        kind_by_handle: Mapping[SyntaxHandle, str],
        range_by_handle: Mapping[SyntaxHandle, SourceRange],
    ) -> None:
        """Bind ordered handles and their syntax facts."""

        self._handles: tuple[SyntaxHandle, ...] = handles
        self._kind_by_handle: Mapping[SyntaxHandle, str] = kind_by_handle
        self._range_by_handle: Mapping[SyntaxHandle, SourceRange] = range_by_handle

    def handles(self, *, kind: str | None = None) -> tuple[SyntaxHandle, ...]:
        """Return syntax handles in deterministic traversal order."""

        if kind is None:
            return self._handles
        return tuple(handle for handle in self._handles if self._kind_by_handle[handle] == kind)

    def kind(self, handle: SyntaxHandle) -> str:
        """Return the Fensu syntax kind for a handle."""

        try:
            return self._kind_by_handle[handle]
        except KeyError as error:
            raise AnalysisLookupError(f"Unknown syntax handle {handle}.") from error

    def range(self, handle: SyntaxHandle) -> SourceRange:
        """Return the source range for a handle."""

        try:
            return self._range_by_handle[handle]
        except KeyError as error:
            raise AnalysisLookupError(f"Unknown syntax handle {handle}.") from error
