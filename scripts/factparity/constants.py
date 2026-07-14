"""Shared constants for fact-backend parity checking."""

from __future__ import annotations

FACT_FAMILY_NAMES: tuple[str, ...] = (
    "annotations",
    "comments",
    "complex_comprehensions",
    "dataclasses",
    "evaluate_rule_calls",
    "function_conditionals",
    "function_contracts",
    "functions",
    "hygiene",
    "meaningful_returns",
    "module_declarations",
    "outer_state_mutations",
    "parameter_mutations",
    "project_calls",
    "project_functions",
    "references",
    "test_functions",
    "test_module",
    "top_level_definition_conditionals",
)
MEANINGFUL_RETURN_PATTERNS: tuple[str, ...] = ("is_*", "get_*", "build_*")
MAX_REPORTED_DIFFS: int = 25
MAX_DIFF_REPR_LENGTH: int = 400
DEFAULT_ROOT_NAMES: tuple[str, ...] = ("src", "tests", "scripts")
