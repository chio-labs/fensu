"""Strata Memory type-layer declarations."""

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
