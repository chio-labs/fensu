"""Shape rule-family types."""

from __future__ import annotations

from enum import StrEnum


class ShapeCode(StrEnum):
    """Stable shape rule codes."""

    TOO_MANY_STATEMENTS = "FFS001"
    TOO_MANY_DISTINCT_CALLS = "FFS002"
    TOO_MANY_LOCALS = "FFS003"
    MAX_ARGUMENTS = "FFS010"
    MAX_STATEMENTS_GLOBAL = "FFS011"
    MEANINGFUL_PROJECT_RESULT_DISCARDED = "FFS101"
    PARAMETER_MUTATION_IN_PHASE_HELPERS = "FFS102"
    DEFAULT_MUTATION_RETURN = "FFS110"
    KEYWORD_ONLY_ARGUMENTS = "FFS120"
    NO_OUTER_STATE_MUTATION = "FFS130"
    NO_COMPLEX_COMPREHENSIONS = "FFS131"
    MUTABLE_RESULT_MODEL = "FFS201"


class ShapeSymbol(StrEnum):
    """Python symbols with shape-rule semantics."""

    DATACLASS = "dataclass"
    FROZEN = "frozen"
