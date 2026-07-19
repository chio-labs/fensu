"""Test-case types for engine operation-count invariants."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class UncachedCountsTestCase:
    """One uncached-run operation envelope expectation."""

    description: str
    file_target: int
    seed: int
    expected_relative_path_computes: int
    expected_min_discovery_nanoseconds: int
    expected_min_full_evaluation_nanoseconds: int
    expected_min_query_cache_hits: int
    expected_min_query_cache_misses: int


@dataclass(frozen=True)
class CachedCountsTestCase:
    """One cold-then-warm operation envelope expectation."""

    description: str
    file_target: int
    seed: int
    expected_warm_fresh_evaluations: int
    expected_warm_parses: int
    expected_warm_manifest_validations: int
    expected_min_warm_cache_bytes_read: int
    expected_min_warm_query_observations: int
    expected_min_warm_fingerprint_nanoseconds: int
    expected_min_warm_cache_evaluation_nanoseconds: int


@dataclass(frozen=True)
class EditCountsTestCase:
    """One single-file-edit incremental expectation."""

    description: str
    file_target: int
    seed: int
    expected_fresh_evaluations: int
    expected_parses: int


@dataclass(frozen=True)
class ChurnCountsTestCase:
    """One complete source-churn cache IO expectation."""

    description: str
    file_target: int
    seed: int
    expected_cache_record_reads: int
    expected_cache_record_scans: int


@dataclass(frozen=True)
class NativeUncachedCountsTestCase:
    """One native-backend uncached-run parse expectation."""

    description: str
    file_target: int
    seed: int
    expected_python_parses: int


@dataclass(frozen=True)
class NativeExecutionBoundaryTestCase:
    """One repository-scale native execution boundary expectation."""

    description: str
    file_target: int
    seed: int
    jobs: int
    expected_worker_partitions: int
    expected_python_parses: int


@dataclass(frozen=True)
class NativeEditCountsTestCase:
    """One native-backend single-file-edit parse expectation."""

    description: str
    file_target: int
    seed: int
    expected_fresh_evaluations: int
    expected_python_parses: int
