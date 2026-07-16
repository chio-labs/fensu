"""Test case types for evaluation engine and RuleContext behavior."""

from __future__ import annotations

from dataclasses import dataclass

from strata.rules.authoring.types import ExecutionOwner, Threshold


@dataclass(frozen=True)
class EvaluationSelectionTestCase:
    """Discovered paths, selection policy, and expected direct targets."""

    description: str
    include: tuple[str, ...]
    exclude: tuple[str, ...]
    expected_paths: tuple[str, ...]
    expected_filtered: bool


@dataclass(frozen=True)
class EvaluationSelectionErrorTestCase:
    """Invalid runtime selection and its expected configuration error."""

    description: str
    include: tuple[str, ...]
    exclude: tuple[str, ...]
    expected_error_fragment: str


@dataclass(frozen=True)
class EvaluationContextSelectionTestCase:
    """Selected requester, excluded context, and expected cross-file behavior."""

    description: str
    expected_codes: tuple[str, ...]
    expected_context_message: str
    expected_evaluated_paths: tuple[str, ...]


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
class CoreContextZoneTestCase:
    """Expected core rule modules using private context analysis zones."""

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
class ThresholdObservationTestCase:
    """A threshold name and expected recorded override resolution."""

    description: str
    threshold: Threshold
    expected_value: int
    expected_pattern: str


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
class ParseDelegationTestCase:
    """Expected shared-factory delegation and direct-parse ownership."""

    description: str
    source: bytes
    expected_factory_calls: int
    expected_direct_parse_paths: tuple[str, ...]


@dataclass(frozen=True)
class EncodedParseErrorTestCase:
    """Invalid encoded source and expected evaluation parse contract."""

    description: str
    source: bytes
    expected_error_fragment: str
    expected_line: int | None
    expected_column: int | None


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
class ExecutionOwnerEvaluationTestCase:
    """One owner plan and expected callback anchor paths."""

    description: str
    files: tuple[tuple[str, str], ...]
    execution_owner: ExecutionOwner
    expected_invocation_paths: tuple[str, ...]


@dataclass(frozen=True)
class PrewarmFamilyPlanTestCase:
    """Mixed-scope sources and the expected per-file native fact-family plans."""

    description: str
    files: tuple[tuple[str, str], ...]
    expected_family_plans: tuple[tuple[str, ...], ...]


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
class WarningTierEvaluationTestCase:
    """Blocking and warning rules with expected provenance-preserving results."""

    description: str
    blocking_code: str
    warning_rule_code: str
    warning_fault_code: str
    expected_fault_codes: tuple[str, ...]
    expected_warning_codes: tuple[str, ...]


@dataclass(frozen=True)
class ScopeFamilySelectionTestCase:
    """Code selection and declared-family execution scope expectations."""

    description: str
    runtime_path: str
    test_path: str
    expected_selected_codes: tuple[str, ...]
    expected_fault_paths: tuple[str, ...]


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
class FileLevelExceptionTestCase:
    """Ownerless fault presence and expected file-level exception outcome."""

    description: str
    expected_applied_exception_count: int
    expected_error_fragment: str | None


@dataclass(frozen=True)
class AnalysisContextTestCase:
    """Source and expected backend-neutral context fault."""

    description: str
    source: str
    expected_line: int
    expected_column: int
    expected_message: str


@dataclass(frozen=True)
class ModuleGateTestCase:
    """One undeclared raw-AST access expectation."""

    description: str
    files: tuple[tuple[str, str], ...]
    expected_error_type: type[Exception]


@dataclass(frozen=True)
class PrewarmSeedTestCase:
    """One native prewarm seeding expectation."""

    description: str
    source: bytes
    expected_reparse_calls: int


@dataclass(frozen=True)
class PrewarmFallbackTestCase:
    """One prewarm skip-and-fallback expectation for unparseable sources."""

    description: str
    source: bytes
    expected_error_type: type[Exception]
