"""Shape rule-family types."""

from __future__ import annotations

from enum import StrEnum


class ShapeCode(StrEnum):
    """Stable shape rule codes."""

    TOO_MANY_STATEMENTS = "SFS001"
    TOO_MANY_DISTINCT_CALLS = "SFS002"
    TOO_MANY_LOCALS = "SFS003"
    MAX_ARGUMENTS = "SFS010"
    MAX_STATEMENTS_GLOBAL = "SFS011"
    MEANINGFUL_PROJECT_RESULT_DISCARDED = "SFS101"
    PARAMETER_MUTATION_IN_PHASE_HELPERS = "SFS102"
    DEFAULT_MUTATION_RETURN = "SFS110"
    KEYWORD_ONLY_ARGUMENTS = "SFS120"
    MUTABLE_RESULT_MODEL = "SFS201"
