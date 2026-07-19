"""Persistent native evaluation-generation models."""

from __future__ import annotations

from dataclasses import dataclass

from strata.cache.fingerprints.models import CacheFingerprint
from strata.evaluation.models import EvaluationResult, FileEvaluation


@dataclass(frozen=True, slots=True)
class CacheIndexEntry:
    """Validated lookup from one source to a native persisted result."""

    path: str
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
    miss_paths: tuple[str, ...]
    hits: int
    misses: int
    invalidations: int
