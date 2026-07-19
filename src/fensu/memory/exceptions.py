"""Exceptions raised by the Fensu Memory domain."""

from __future__ import annotations


class MemoryError(Exception):
    """Base error for Fensu Memory operations."""


class MemoryDisabledError(MemoryError):
    """Raised when Fensu Memory is disabled for the active project."""


class MemoryOperationError(MemoryError):
    """Raised when the native memory engine cannot complete an operation."""


class MemoryRelationNotFoundError(MemoryError):
    """Raised when focused schema metadata names no public memory relation."""
