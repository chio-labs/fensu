"""Exceptions raised by the Fensu Memory domain."""

from __future__ import annotations


class MemoryError(Exception):
    """Base error for Fensu Memory operations."""


class MemoryOperationError(MemoryError):
    """Raised when the native memory engine cannot complete an operation."""
