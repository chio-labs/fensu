"""Call-map provider contracts."""

from __future__ import annotations

from typing import Protocol

from strata.config.core.models import Config
from strata.mapping.core.models import CallMapNode


class CallMapProvider(Protocol):
    """Replaceable provider for deterministic project call maps."""

    def __call__(self, *, config: Config, symbol: str, depth: int) -> CallMapNode:
        """Build a downstream call map for one symbol."""
        ...
