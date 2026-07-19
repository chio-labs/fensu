"""Hygiene rule-family types."""

from __future__ import annotations

from enum import StrEnum


class HygieneCode(StrEnum):
    """Stable hygiene rule codes."""

    SINGLE_LINE_DOCSTRINGS = "FFH001"
    NO_STANDALONE_COMMENTS = "FFH002"
    NO_RAW_BUILTIN_RAISE = "FFH003"
    NO_ASSERT_IN_RUNTIME = "FFH004"
    NO_SWALLOWED_EXCEPTION_PROBE = "FFH005"
    NO_COMPLEX_COMPREHENSIONS_IN_TOOLING = "FFH006"
    NO_UNNAMED_STRING_DECISIONS = "FFH007"
    NO_MAGIC_NUMERIC_COMPARISONS = "FFH008"
    NO_IMPORT_TIME_SIDE_EFFECTS = "FFH009"
