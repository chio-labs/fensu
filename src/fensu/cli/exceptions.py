"""Exceptions raised while adapting CLI commands."""

from __future__ import annotations


class CliCommandError(Exception):
    """Raised when one selected command cannot complete its operation."""
