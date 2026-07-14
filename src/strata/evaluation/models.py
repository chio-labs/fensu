"""Evaluation runtime models."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from strata.analysis.classes.lazy_syntax_artifacts import LazySyntaxArtifacts
from strata.analysis.models import ProjectDependency
from strata.analysis.types import Analysis
from strata.discovery.models import PositionFacts, ScopedFile
from strata.rules.authoring.models import CustomRuleRegistration, Fault
from strata.rules.authoring.types import Threshold


@dataclass(frozen=True, slots=True)
class ParsedModule:
    """A discovered Python file plus lazily shared CPython traversal facts."""

    scoped_file: ScopedFile
    source: str
    source_fingerprint: str
    syntax_artifacts: LazySyntaxArtifacts
    position: PositionFacts
    analysis: Analysis


@dataclass(frozen=True, slots=True)
class RuleExceptionKey:
    """One exact configured rule and path exception, optionally symbol-scoped."""

    rule: str
    path: str
    symbol: str | None


@dataclass(frozen=True, slots=True)
class ThresholdOverrideUse:
    """One matching threshold override actually consulted by an active rule."""

    threshold: Threshold
    effective_value: int
    matched_pattern: str
    reason: str
    override_order: int
    repository_path: str


@dataclass(frozen=True, slots=True)
class SourceSnapshot:
    """Exact source bytes and their stable content identity."""

    content: bytes
    fingerprint: str


@dataclass(frozen=True, slots=True)
class ExternalAnalysisBuild:
    """Tolerant external analysis plus the readable source identity."""

    analysis: Analysis | None
    source_fingerprint: str | None


@dataclass(frozen=True, slots=True)
class EvaluationSelection:
    """Direct evaluation targets selected from a complete discovered tree."""

    files: tuple[ScopedFile, ...]
    discovered_count: int
    excluded_count: int
    filtered: bool


@dataclass(frozen=True, slots=True)
class EvaluationTarget:
    """One source-owned normal and/or supplemental evaluation target."""

    scoped_file: ScopedFile
    direct: bool
    custom_rule_registrations: tuple[CustomRuleRegistration, ...] = ()
    custom_rule_coverage_warning: bool = False


@dataclass(frozen=True, slots=True)
class FileEvaluation:
    """Unrendered evaluation output and observed inputs for one source file."""

    path: Path
    source_fingerprint: str
    faults: tuple[Fault, ...]
    applied_exception_keys: tuple[RuleExceptionKey, ...]
    dependencies: tuple[ProjectDependency, ...]
    warnings: tuple[Fault, ...] = ()
    threshold_override_uses: tuple[ThresholdOverrideUse, ...] = ()


@dataclass(frozen=True, slots=True)
class EvaluationResult:
    """Evaluation output for a discovered tree."""

    faults: tuple[Fault, ...]
    warnings: tuple[Fault, ...] = ()
    applied_exception_count: int = 0
    dependencies: tuple[ProjectDependency, ...] = ()
    file_evaluations: tuple[FileEvaluation, ...] = ()
    threshold_override_uses: tuple[ThresholdOverrideUse, ...] = ()
    selection: EvaluationSelection | None = None
