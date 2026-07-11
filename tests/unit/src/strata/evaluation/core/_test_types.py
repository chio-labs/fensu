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
class SourceFingerprintTestCase:
    """Raw source bytes and expected parsed source identity."""

    description: str
    source: bytes
    expected_source: str
    expected_fingerprint: str


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
class ProjectRetentionTestCase:
    """Project-query order and expected strict parse count."""

    description: str
    file_name: str
    query_first: bool
    expected_parse_count: int


@dataclass(frozen=True)
class ProjectParseContractTestCase:
    """Malformed discovered source and expected strict parse failure."""

    description: str
    source: str
    expected_error_type: type[Exception]


@dataclass(frozen=True)
class ProjectDependencyTestCase:
    """Missing module query and expected candidate dependencies."""

    description: str
    module_name: str
    expected_dependency_paths: tuple[str, ...]
    expected_dependency_kinds: tuple[str, ...]
    expected_dependency_answers: tuple[bool, ...]
    runtime_roots: tuple[str, ...] = ("src/pkg",)
    test_roots: tuple[str, ...] = ()


@dataclass(frozen=True)
class ProjectDependencyEvaluationTestCase:
    """Source and expected dependency propagated through evaluation."""

    description: str
    source: str
    expected_dependency_name: str
    expected_dependency_kind: str
    expected_dependency_answer: bool


@dataclass(frozen=True)
class ProjectDirectoryQueryTestCase:
    """Directory contents and expected aggregate dependency metadata."""

    description: str
    expected_entry_names: tuple[str, ...]
    expected_direct_matches: tuple[str, ...]
    expected_recursive_matches: tuple[str, ...]
    expected_dependency_kinds: tuple[str, ...]
    expected_patterns: tuple[str | None, ...]
    expected_recursive: tuple[bool, ...]


@dataclass(frozen=True)
class ProjectScalarQueryTestCase:
    """Scalar filesystem queries and their expected frozen answers."""

    description: str
    expected_dependency_kinds: tuple[str, ...]
    expected_dependency_answers: tuple[bool, ...]


@dataclass(frozen=True)
class ProjectSourceQueryTestCase:
    """Repeated source query and expected frozen answer ownership."""

    description: str
    source: str
    mutated_source: str
    expected_dependency_count: int


@dataclass(frozen=True)
class FileEvaluationTestCase:
    """One-file source and expected unrendered evaluation boundary."""

    description: str
    file_path: str
    source: str
    expected_fault_codes: tuple[str, ...]
    expected_dependency_answers: tuple[bool, ...]
    expected_applied_exception_keys: int


@dataclass(frozen=True)
class FileEvaluationExceptionTestCase:
    """One-file exception and expected retained suppression state."""

    description: str
    file_path: str
    source: str
    expected_fault_count: int
    expected_applied_symbols: tuple[str, ...]


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


@dataclass(frozen=True)
class AnalysisContextTestCase:
    """Source and expected backend-neutral context fault."""

    description: str
    source: str
    expected_line: int
    expected_column: int
    expected_message: str
