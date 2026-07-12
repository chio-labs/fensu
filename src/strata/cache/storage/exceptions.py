"""Persistent cache storage exceptions."""

from __future__ import annotations


class CachePathError(Exception):
    """Raised when a cache entry path escapes its versioned storage root."""


class CacheRecordError(Exception):
    """Raised when a record cannot be represented by the cache schema."""
