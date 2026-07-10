"""Call-map provider contracts."""

from __future__ import annotations

from typing import Literal, Protocol

from strata.mapping.core.models import CallMapNode, MappingSource

type PathMode = Literal["absolute", "relative", "compact", "none"]


class CallMapProvider(Protocol):
    """Replaceable provider for deterministic project call maps."""

    def __call__(
        self, *, sources: tuple[MappingSource, ...], symbol: str, depth: int
    ) -> CallMapNode:
        """Build a downstream call map for one symbol."""
        ...
