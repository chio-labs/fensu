"""Naming rule-family types."""

from __future__ import annotations

from enum import StrEnum


class NamingCode(StrEnum):
    """Stable naming rule codes."""

    VALIDATOR_MUST_NOT_RETURN = "SFN001"
