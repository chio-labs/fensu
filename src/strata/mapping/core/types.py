"""Call-map provider contracts."""

from __future__ import annotations

from enum import StrEnum
from typing import Protocol

from strata.mapping.core.models import CallMapNode, MappingSource


class PathMode(StrEnum):
    """Supported call-map path display modes."""

    ABSOLUTE = "absolute"
    RELATIVE = "relative"
    COMPACT = "compact"
    NONE = "none"


class CallMapProvider(Protocol):
    """Replaceable provider for deterministic project call maps."""

    def __call__(
        self, *, sources: tuple[MappingSource, ...], symbol: str, depth: int
    ) -> CallMapNode:
        """Build a downstream call map for one symbol."""
        ...
