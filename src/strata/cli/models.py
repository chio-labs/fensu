"""Structured models for CLI command orchestration."""

from __future__ import annotations

from dataclasses import dataclass

from strata.cache.fingerprints.models import CacheFingerprint
from strata.cache.results.models import CachedCheckOutput, CacheStats
from strata.evaluation.models import EvaluationResult


@dataclass(frozen=True, slots=True)
class CheckEvaluation:
    """Evaluated diagnostics plus cache observability for one check run."""

    result: EvaluationResult | None
    stats: CacheStats | None
    disabled_reason: str | None
    short_circuit: CachedCheckOutput | None
    surface_targets: tuple[str, ...] | None
    global_fingerprint: CacheFingerprint | None
    surface_index_fingerprint: CacheFingerprint | None
