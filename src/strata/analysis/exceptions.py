"""Source-analysis exceptions."""

from __future__ import annotations

from pathlib import Path


class PythonSourceParseError(Exception):
    """Raised when exact Python source bytes cannot be parsed."""

    def __init__(
        self,
        *,
        path: Path,
        message: str,
        line: int | None,
        column: int | None,
        rendered: str,
    ) -> None:
        """Store the backend-neutral syntax diagnostic."""

        super().__init__(rendered)
        self.path: Path = path
        self.message: str = message
        self.line: int | None = line
        self.column: int | None = column


class AnalysisLookupError(LookupError):
    """Raised when a query uses a handle outside its analysis context."""
