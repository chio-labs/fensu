"""Fensu Memory type-layer declarations."""

from __future__ import annotations

from enum import StrEnum

type MemoryQueryValue = (
    None | bool | int | float | str | list[MemoryQueryValue] | dict[str, MemoryQueryValue]
)


class MemoryQueryFormat(StrEnum):
    """Supported memory query output formats."""

    LONG = "long"
    TABLE = "table"
    JSON = "json"
    CSV = "csv"


class MemoryGraphDirection(StrEnum):
    """Supported memory graph traversal directions."""

    OUTBOUND = "outbound"
    INBOUND = "inbound"
    BOTH = "both"


class MemoryGraphRelationship(StrEnum):
    """Supported memory graph relationship filters."""

    LINK = "link"
    RELATED = "related"
    DEPENDS_ON = "depends-on"
    SUPERSEDES = "supersedes"
    DISCOVERED_FROM = "discovered-from"
    IMPLEMENTS = "implements"
    DOCUMENTS = "documents"


class MemoryGraphFormat(StrEnum):
    """Supported memory graph output formats."""

    LONG = "long"
    JSON = "json"
