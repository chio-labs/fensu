"""Persistent evaluation-result cache models."""

from __future__ import annotations

from dataclasses import dataclass

from strata.analysis.types import ProjectDependencyKind
from strata.cache.fingerprints.models import CacheFingerprint
from strata.cache.fingerprints.types import CanonicalValue
from strata.cache.results.types import DependencyAnswer
from strata.cache.storage.models import CacheRecord
from strata.evaluation.models import EvaluationResult


@dataclass(frozen=True, slots=True)
class CacheMetadata:
    """Identity of the global inputs owning the active cache generation."""

    global_fingerprint: CacheFingerprint


@dataclass(frozen=True, slots=True)
class CacheIndexEntry:
    """Lookup from one discovered source to its persisted evaluation result."""

    path: str
    source_fingerprint: CacheFingerprint
    result_fingerprint: CacheFingerprint
    record_fingerprint: CacheFingerprint


@dataclass(frozen=True, slots=True)
class CacheIndex:
    """Deterministic result lookup bound to one global fingerprint."""

    global_fingerprint: CacheFingerprint
    entries: tuple[CacheIndexEntry, ...]
    dependencies_fingerprint: CacheFingerprint | None = None
    collection_fingerprint: CacheFingerprint | None = None


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
class CacheLookup:
    """Integrity and dependency validation outcome for one indexed candidate."""

    result: CachedFileResult | None
    missed: bool
    invalidated: bool


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
class CheckCacheContext:
    """Validated index, rendered-output surface, and aggregated observations."""

    index: CacheIndex | None
    output: CachedCheckOutput | None
    observations: tuple[DependencyObservation, ...] | None
    index_fingerprint: CacheFingerprint | None = None


@dataclass(frozen=True, slots=True)
class EditReplaySurface:
    """Validated aggregate observations and collection inputs for edit replay."""

    observations: tuple[DependencyObservation, ...]
    contributions: tuple[CachedCollectionContribution, ...]


@dataclass(frozen=True, slots=True)
class CacheEvaluation:
    """Complete logical evaluation plus observable cache operation counts."""

    result: EvaluationResult | None
    stats: CacheStats
    short_circuit: CachedCheckOutput | None = None
    surface_targets: tuple[str, ...] | None = None
    surface_index_fingerprint: CacheFingerprint | None = None


@dataclass(frozen=True, slots=True)
class DependencyObservation:
    """One project query and the complete answer consumed by evaluation."""

    requester_path: str
    query_path: str
    dependency_path: str
    kind: ProjectDependencyKind
    answer: DependencyAnswer
    pattern: str | None = None
    recursive: bool = False


@dataclass(frozen=True, slots=True)
class CachedFault:
    """Backend-neutral persisted representation of one rule finding."""

    code: str
    path: str
    message: str
    line: int | None = None
    column: int | None = None
    remediation: str | None = None


@dataclass(frozen=True, slots=True)
class CachedRuleExceptionKey:
    """One exact configured exception consumed by file evaluation."""

    rule: str
    path: str
    symbol: str | None


@dataclass(frozen=True, slots=True)
class CachedThresholdOverrideUse:
    """Persisted representation of one consulted matching threshold override."""

    threshold: str
    effective_value: int
    matched_pattern: str
    reason: str
    override_order: int
    repository_path: str


@dataclass(frozen=True, slots=True)
class CachedCollectionContribution:
    """One file's nonempty global-collection inputs within a cache generation."""

    path: str
    faults: tuple[CachedFault, ...]
    warnings: tuple[CachedFault, ...]
    applied_exception_keys: tuple[CachedRuleExceptionKey, ...]
    threshold_override_uses: tuple[CachedThresholdOverrideUse, ...]


@dataclass(frozen=True, slots=True)
class CachedFileResult:
    """Complete reusable output and observed inputs for one source file."""

    path: str
    source_fingerprint: CacheFingerprint
    faults: tuple[CachedFault, ...]
    applied_exception_keys: tuple[CachedRuleExceptionKey, ...]
    dependencies: tuple[DependencyObservation, ...]
    warnings: tuple[CachedFault, ...] = ()
    threshold_override_uses: tuple[CachedThresholdOverrideUse, ...] = ()


@dataclass(frozen=True, slots=True)
class PreparedFileResult:
    """One converted file result paired with its validated storage record."""

    result: CachedFileResult
    record: CacheRecord


@dataclass(frozen=True, slots=True)
class PublicationCandidate:
    """One fresh cacheable result prepared for transactional publication."""

    entry: CacheIndexEntry
    encoded: bytes


@dataclass(frozen=True, slots=True)
class PublicationPreparation:
    """Encoded publication candidates and per-file conversion outcomes."""

    candidates: tuple[PublicationCandidate, ...]
    non_cacheable: int
    internal_error: bool
    observations: tuple[DependencyObservation, ...] = ()
    observations_conflicted: bool = False


@dataclass(frozen=True, slots=True)
class CachedFact:
    """Independently tagged backend-neutral fact payload reserved for later reuse."""

    path: str
    source_fingerprint: CacheFingerprint
    fact_kind: str
    payload: CanonicalValue
