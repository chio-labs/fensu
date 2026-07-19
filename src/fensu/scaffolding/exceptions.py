"""Errors raised while detecting or planning repository scaffolding."""

from __future__ import annotations


class ScaffoldingError(Exception):
    """Base error for repository scaffolding failures."""


class PyprojectParseError(ScaffoldingError):
    """Raised when repository packaging metadata is invalid TOML."""


class RepositoryDetectionError(ScaffoldingError):
    """Raised when a repository cannot be safely inspected."""


class InitError(ScaffoldingError):
    """Raised when initialization cannot safely complete."""


class InitRefusalError(InitError):
    """Raised when initialization is declined or already configured."""
