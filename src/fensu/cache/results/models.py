"""Persistent native evaluation-generation models."""

from __future__ import annotations

from dataclasses import dataclass

from fensu.cache.fingerprints.models import CacheFingerprint
from fensu.evaluation.models import (
    EvaluationResult,
    EvaluationSelection,
    EvaluationTarget,
    FileEvaluation,
    ProjectEvaluation,
)
from fensu.rules.authoring.models import RuleSpec


@dataclass(frozen=True, slots=True)
class CacheIndexEntry:
    """Validated lookup from one source to a native persisted result."""

    subject_kind: str
    subject_identity: str
    source_fingerprint: CacheFingerprint
    result_fingerprint: CacheFingerprint
    record_fingerprint: CacheFingerprint


@dataclass(frozen=True, slots=True)
class CacheStats:
    """Observable cache operation counts for one logical evaluation."""

    hits: int = 0
    misses: int = 0
    invalidations: int = 0
    writes: int = 0
    non_cacheable: int = 0
    storage_failed: bool = False
    internal_error: bool = False
    index_fingerprint: CacheFingerprint | None = None


@dataclass(frozen=True, slots=True)
class CachedCheckOutput:
    """One complete rendered check surface bound to a cache generation."""

    global_fingerprint: CacheFingerprint
    index_fingerprint: CacheFingerprint
    targets: tuple[str, ...]
    plain_output: str
    color_output: str
    exit_code: int


@dataclass(frozen=True, slots=True)
class CacheEvaluation:
    """Complete logical evaluation plus observable cache operation counts."""

    result: EvaluationResult | None
    stats: CacheStats
    short_circuit: CachedCheckOutput | None = None
    surface_targets: tuple[str, ...] | None = None
    surface_index_fingerprint: CacheFingerprint | None = None


@dataclass(frozen=True, slots=True)
class NativeGenerationPlan:
    """Native cache decisions and validated reusable collection inputs."""

    mode: str
    index_fingerprint: CacheFingerprint | None
    retained_entries: tuple[CacheIndexEntry, ...]
    cached_evaluations: tuple[FileEvaluation, ...]
    retained_evaluations: tuple[FileEvaluation, ...]
    cached_project_evaluation: ProjectEvaluation | None
    retained_project_evaluation: ProjectEvaluation | None
    miss_paths: tuple[str, ...]
    hits: int
    misses: int
    invalidations: int


@dataclass(frozen=True, slots=True)
class SubjectRulePartitions:
    """File and project rule selections preserving configured order."""

    file_rules: tuple[RuleSpec, ...]
    file_warnings: tuple[RuleSpec, ...]
    project_rules: tuple[RuleSpec, ...]
    project_warnings: tuple[RuleSpec, ...]


@dataclass(frozen=True, slots=True)
class RuleScopes:
    """Fresh and cacheable rule selections for one subject kind."""

    fresh_ruleset: tuple[RuleSpec, ...]
    fresh_warning_rules: tuple[RuleSpec, ...]
    cacheable_ruleset: tuple[RuleSpec, ...]
    cacheable_warning_rules: tuple[RuleSpec, ...]
    scoped: bool
    fully_fresh: bool


@dataclass(frozen=True, slots=True)
class CachedEvaluationSetup:
    """Prepared subject partitions, selection, targets, and cache scopes."""

    partitions: SubjectRulePartitions
    selection: EvaluationSelection
    targets: tuple[EvaluationTarget, ...]
    file_scopes: RuleScopes
    project_scopes: RuleScopes
