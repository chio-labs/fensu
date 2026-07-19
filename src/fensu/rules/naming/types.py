"""Naming rule-family types."""

from __future__ import annotations

from enum import StrEnum


class NamingCode(StrEnum):
    """Stable naming rule codes."""

    VALIDATOR_MUST_NOT_RETURN = "FFN001"
    PREDICATE_MUST_RETURN_BOOL = "FFN002"
    VALUE_NAME_MUST_RETURN_VALUE = "FFN003"
    ITERATOR_NAME_MUST_PRODUCE_ITERATOR = "FFN004"
