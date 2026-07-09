"""Hygiene rule-family types."""

from __future__ import annotations

from enum import StrEnum


class HygieneCode(StrEnum):
    """Stable hygiene rule codes."""

    SINGLE_LINE_DOCSTRINGS = "SFX001"
    NO_STANDALONE_COMMENTS = "SFX002"
    NO_RAW_BUILTIN_RAISE = "SFX003"
    NO_ASSERT_IN_RUNTIME = "SFX004"
    NO_SWALLOWED_EXCEPTION_PROBE = "SFX005"
