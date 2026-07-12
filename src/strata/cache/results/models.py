"""Persistent evaluation-result cache models."""

from __future__ import annotations

from dataclasses import dataclass

from strata.analysis.core.types import ProjectDependencyKind
from strata.cache.fingerprints.models import CacheFingerprint
from strata.cache.fingerprints.types import CanonicalValue
from strata.cache.results.types import DependencyAnswer
from strata.cache.storage.models import CacheRecord
from strata.evaluation.core.models import EvaluationResult


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


@dataclass(frozen=True, slots=True)
class CacheLookup:
    """Integrity and dependency validation outcome for one indexed candidate."""

    result: CachedFileResult | None
    missed: bool
    invalidated: bool


@dataclass(frozen=True, slots=True)
class CacheEvaluation:
    """Complete logical evaluation plus observable cache operation counts."""

    result: EvaluationResult
    stats: CacheStats


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
    symbol: str


@dataclass(frozen=True, slots=True)
class CachedFileResult:
    """Complete reusable output and observed inputs for one source file."""

    path: str
    source_fingerprint: CacheFingerprint
    faults: tuple[CachedFault, ...]
    applied_exception_keys: tuple[CachedRuleExceptionKey, ...]
    dependencies: tuple[DependencyObservation, ...]


@dataclass(frozen=True, slots=True)
class PublicationCandidate:
    """One fresh cacheable result prepared for transactional publication."""

    entry: CacheIndexEntry
    record: CacheRecord


@dataclass(frozen=True, slots=True)
class PublicationPreparation:
    """Encoded publication candidates and per-file conversion outcomes."""

    candidates: tuple[PublicationCandidate, ...]
    non_cacheable: int
    internal_error: bool


@dataclass(frozen=True, slots=True)
class CachedFact:
    """Independently tagged backend-neutral fact payload reserved for later reuse."""

    path: str
    source_fingerprint: CacheFingerprint
    fact_kind: str
    payload: CanonicalValue
