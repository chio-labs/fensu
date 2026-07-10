"""Test case types for backend-neutral source analysis."""

from dataclasses import dataclass


@dataclass(frozen=True)
class SourceAnalysisTestCase:
    """Source and expected syntax, relation, and text facts."""

    description: str
    source: str
    selected_kind: str
    expected_text: str
    expected_line: int
    expected_column: int
    expected_ancestor_kinds: tuple[str, ...]


@dataclass(frozen=True)
class AnalysisErrorTestCase:
    """Source and expected analysis query error."""

    description: str
    source: str
    expected_error_type: type[Exception]


@dataclass(frozen=True)
class OuterStateFactTestCase:
    """Source and expected backend-neutral outer-state mutation fact."""

    description: str
    source: str
    expected_fact_count: int
    expected_line: int
    expected_text: str
