"""Evaluation exceptions."""

from __future__ import annotations

from pathlib import Path


class ParseError(Exception):
    """Raised when a Python file cannot be parsed by the running interpreter."""

    def __init__(self, *, path: Path, message: str, line: int | None, column: int | None) -> None:
        """Store parse diagnostic location and text."""

        super().__init__(message)
        self.path: Path = path
        self.message: str = message
        self.line: int | None = line
        self.column: int | None = column
