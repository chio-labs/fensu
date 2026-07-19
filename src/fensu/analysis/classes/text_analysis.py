"""Python source-text analysis implementation."""

from __future__ import annotations

from pathlib import Path

from fensu.analysis.exceptions import AnalysisLookupError
from fensu.analysis.models import SourceRange


class PythonTextAnalysis:
    """Source-text queries backed by an immutable Python string."""

    def __init__(self, *, path: Path, source: str) -> None:
        """Bind source text and its owning path."""

        self._path: Path = path
        self._source: str = source
        self._source_bytes: bytes = source.encode("utf-8")
        self._lines: tuple[str, ...] = tuple(source.splitlines())

    @property
    def source(self) -> str:
        """Return the complete source text."""

        return self._source

    def line(self, line_number: int) -> str:
        """Return one source line without its line ending."""

        if line_number < 1 or line_number > len(self._lines):
            raise AnalysisLookupError(f"Source line {line_number} does not exist in {self._path}.")
        return self._lines[line_number - 1]

    def slice(self, source_range: SourceRange) -> str:
        """Return the text covered by an end-exclusive source range."""

        if source_range.path != self._path:
            raise AnalysisLookupError(
                f"Source range belongs to {source_range.path}, not {self._path}."
            )
        return self._source_bytes[source_range.start.offset : source_range.end.offset].decode(
            "utf-8"
        )
