"""Hygiene rule-family types."""

from __future__ import annotations

from enum import StrEnum


class HygieneCode(StrEnum):
    """Stable hygiene rule codes."""

    SINGLE_LINE_DOCSTRINGS = "SFH001"
    NO_STANDALONE_COMMENTS = "SFH002"
    NO_RAW_BUILTIN_RAISE = "SFH003"
    NO_ASSERT_IN_RUNTIME = "SFH004"
    NO_SWALLOWED_EXCEPTION_PROBE = "SFH005"
    NO_COMPLEX_COMPREHENSIONS_IN_TOOLING = "SFH006"
    NO_UNNAMED_STRING_DECISIONS = "SFH007"
    NO_MAGIC_NUMERIC_COMPARISONS = "SFH008"
    NO_IMPORT_TIME_SIDE_EFFECTS = "SFH009"
