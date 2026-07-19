"""Call-map provider contracts."""

from __future__ import annotations

from enum import StrEnum
from typing import Protocol

from strata.mapping.models import CallMapNode, ClassDefinition, FunctionDefinition, MappingSource


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


class SymbolResolver(Protocol):
    """Point-lookup interface used while resolving a call tree."""

    def get_function(self, key: str) -> FunctionDefinition | None:
        """Return one function by canonical key."""
        ...

    def get_class(self, key: str) -> ClassDefinition | None:
        """Return one class by canonical key."""
        ...

    def get_protocol_implementations(self, key: str) -> tuple[ClassDefinition, ...]:
        """Return concrete project classes nominally implementing one protocol."""
        ...
