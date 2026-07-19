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
    NO_OUTER_STATE_MUTATION = "SFS130"
    NO_COMPLEX_COMPREHENSIONS = "SFS131"
    MUTABLE_RESULT_MODEL = "SFS201"


class ShapeSymbol(StrEnum):
    """Python symbols with shape-rule semantics."""

    DATACLASS = "dataclass"
    FROZEN = "frozen"
