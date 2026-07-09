"""Discovery exceptions raised while resolving configured scopes."""

from __future__ import annotations


class RepoRootNotFoundError(Exception):
    """Raised when configured code roots cannot be resolved from the repo root."""
