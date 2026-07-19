"""Discovery exceptions raised while resolving configured scopes."""

from __future__ import annotations

from fensu.config.exceptions import ConfigError


class RepoRootNotFoundError(ConfigError):
    """Raised when configured code roots cannot be resolved from the repo root."""
