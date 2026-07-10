"""Test case types for evaluation engine and RuleContext behavior."""

from __future__ import annotations

from dataclasses import dataclass

from strata.rules.authoring.types import Threshold


@dataclass(frozen=True)
class AstAccessTestCase:
    """Source text plus expected AST helper results."""

    description: str
    source: str
    expected_call_count: int
    expected_distinct_callees: frozenset[str]
    expected_assigned_locals: frozenset[str]
    expected_parameter_names: frozenset[str]


@dataclass(frozen=True)
class AstIndexTestCase:
    """Expected operation counts from combined AST index construction."""

    description: str
    source: str
    expected_node_count: int
    expected_parent_count: int
    expected_child_scan_count: int


@dataclass(frozen=True)
class CoreWalkTestCase:
    """Expected core rule modules retaining a deliberate full-module AST walk."""

    description: str
    expected_paths: tuple[str, ...]


@dataclass(frozen=True)
class EvaluationFaultTestCase:
    """Source files and expected sorted fault render facts."""

    description: str
    files: tuple[tuple[str, str], ...]
    expected_fault_codes: tuple[str, ...]
    expected_fault_lines: tuple[int | None, ...]


@dataclass(frozen=True)
class ContextThresholdTestCase:
    """A file role and expected threshold lookup value."""

    description: str
    file_path: str
    threshold: Threshold
    expected_threshold: int


@dataclass(frozen=True)
class ParseErrorTestCase:
    """Invalid source and expected parse diagnostic fragment."""

    description: str
    source: str
    expected_error_fragment: str
    expected_line: int
    expected_column: int


@dataclass(frozen=True)
class ContextPropertyTestCase:
    """Source file and expected context property report."""

    description: str
    file_path: str
    source: str
    expected_message_prefix: str
    expected_message_suffix: str


@dataclass(frozen=True)
class FaultFactoryTestCase:
    """Fault factory source and expected message/remediation behavior."""

    description: str
    source: str
    expected_messages: tuple[str, ...]
    expected_remediations: tuple[str | None, ...]


@dataclass(frozen=True)
class EmptyEvaluationTestCase:
    """Source files and expected empty evaluation result."""

    description: str
    files: tuple[tuple[str, str], ...]
    expected_fault_count: int


@dataclass(frozen=True)
class EvaluationOperationTestCase:
    """Source files and expected once-per-file engine operation counts."""

    description: str
    files: tuple[tuple[str, str], ...]
    expected_parse_count: int
    expected_position_count: int
    expected_routing_count: int


@dataclass(frozen=True)
class AstHelperContextTestCase:
    """Source files and expected ctx AST helper message."""

    description: str
    files: tuple[tuple[str, str], ...]
    expected_fault_codes: tuple[str, ...]
    expected_fault_lines: tuple[int | None, ...]
    expected_message: str


@dataclass(frozen=True)
class RuleExceptionEvaluationTestCase:
    """Source exceptions and expected retained evaluation result."""

    description: str
    source: str
    symbols: tuple[str, ...]
    expected_fault_lines: tuple[int | None, ...]
    expected_applied_exception_count: int
    expected_error_fragment: str | None


@dataclass(frozen=True)
class RuleExceptionTargetTestCase:
    """Configured target and expected semantic validation error."""

    description: str
    path: str
    symbol: str
    create_path: bool
    expected_error_fragment: str
