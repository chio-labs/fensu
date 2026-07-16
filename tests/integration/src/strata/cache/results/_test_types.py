"""Test case types for persistent typed cache records."""

from __future__ import annotations

from dataclasses import dataclass

from strata.cache.results.models import CachedFileResult, CacheIndex


@dataclass(frozen=True)
class PersistentTypedResultTestCase:
    """One typed result and expected cross-store persistence behavior."""

    description: str
    relative_path: str
    result: CachedFileResult
    expected_write: bool
    expected_result: CachedFileResult


@dataclass(frozen=True)
class InvalidCachedRuleCodeTestCase:
    """One invalid cached fault code and expected serialization error."""

    description: str
    rule_code: str
    expected_error_type: type[Exception]


@dataclass(frozen=True)
class ResultCachePersistenceTestCase:
    """One published file evaluation and expected repository behavior."""

    description: str
    relative_path: str
    expected_index_entries: int
    expected_misses: int
    expected_writes: int
    expected_non_cacheable: int


@dataclass(frozen=True)
class ResultCacheMissTestCase:
    """One cache mismatch and expected safe miss."""

    description: str
    relative_path: str
    expected_result: CachedFileResult | None
    expected_missed: bool = False
    expected_invalidated: bool = False


@dataclass(frozen=True)
class ResultCachePublicationFailureTestCase:
    """One failed transaction and expected unpublished result counts."""

    description: str
    relative_path: str
    expected_writes: int
    expected_index: CacheIndex | None


@dataclass(frozen=True)
class ResultCacheCandidateTestCase:
    """One indexed candidate and expected validation transitions."""

    description: str
    relative_path: str
    expected_initial_invalidated: bool
    expected_source_invalidated: bool
    expected_dependency_invalidated: bool


@dataclass(frozen=True)
class CachedEvaluationReuseTestCase:
    """Cold and warm evaluation counts with expected diagnostic parity."""

    description: str
    relative_path: str
    source: str
    expected_cold_hits: int
    expected_cold_misses: int
    expected_warm_hits: int
    expected_warm_misses: int
    expected_warm_writes: int
    expected_fault_count: int


@dataclass(frozen=True)
class CachedEvaluationSelectionTestCase:
    """Selected target and excluded dependency with expected cache transitions."""

    description: str
    expected_discovered_count: int
    expected_target_count: int
    expected_cold_misses: int
    expected_warm_hits: int
    expected_invalidations: int
    expected_changed_message: str


@dataclass(frozen=True)
class CachedNamingParityTestCase:
    """Naming faults and expected cold/warm persistent cache parity."""

    description: str
    relative_path: str
    source: str
    expected_codes: tuple[str, ...]
    expected_warm_hits: int


@dataclass(frozen=True)
class CachedEvaluationInvalidationTestCase:
    """One input mutation and expected recomputed diagnostic state."""

    description: str
    relative_path: str
    first_source: str
    second_source: str
    expected_invalidations: int
    expected_message: str


@dataclass(frozen=True)
class CachedResultReadFilteringTestCase:
    """Source mutations and expected old-result read boundaries."""

    description: str
    initial_files: tuple[tuple[str, str], ...]
    changed_files: tuple[tuple[str, str], ...]
    expected_loaded_paths: tuple[str, ...]
    expected_invalidations: int


@dataclass(frozen=True)
class EditReplayDependencyTestCase:
    """One edit changing a queried answer and the expected dependent updates."""

    description: str
    initial_context_source: str
    changed_context_source: str
    expected_invalidations: int
    expected_messages: tuple[str, ...]


@dataclass(frozen=True)
class EditReplayFastPathTestCase:
    """One independent edit and the expected zero-result-read replay."""

    description: str
    initial_target_source: str
    changed_target_source: str
    expected_invalidations: int
    expected_loaded_paths: tuple[str, ...]
    expected_messages: tuple[str, ...]


@dataclass(frozen=True)
class CachedDomainShapeInvalidationTestCase:
    """One namespace-source transition and expected cached SFR306 invalidation."""

    description: str
    role_relative_path: str
    asset_relative_path: str
    namespace_relative_path: str
    expected_initial_codes: tuple[str, ...]
    expected_invalidations: int
    expected_misses: int
    expected_changed_codes: tuple[str, ...]


@dataclass(frozen=True)
class CachedLeafMainInvalidationTestCase:
    """One added main entry and expected cached SFR309 invalidation."""

    description: str
    role_relative_path: str
    main_relative_path: str
    expected_initial_codes: tuple[str, ...]
    expected_invalidations: int
    expected_misses: int
    expected_changed_codes: tuple[str, ...]


@dataclass(frozen=True)
class CachedSharedDomainPrefixInvalidationTestCase:
    """One added sibling domain and expected cached SFR308 invalidation."""

    description: str
    first_domain_path: str
    second_domain_path: str
    expected_initial_codes: tuple[str, ...]
    expected_invalidations: int
    expected_changed_codes: tuple[str, ...]


@dataclass(frozen=True)
class CachedEvaluationManifestTestCase:
    """Changed discovered manifest and expected hit/miss composition."""

    description: str
    initial_files: tuple[str, ...]
    final_files: tuple[str, ...]
    expected_hits: int
    expected_misses: int
    expected_invalidations: int
    expected_fault_paths: tuple[str, ...]


@dataclass(frozen=True)
class CachedEvaluationRetentionTestCase:
    """One mixed hit/invalidation publication and expected later full reuse."""

    description: str
    relative_paths: tuple[str, ...]
    edited_path: str
    second_source: str
    expected_third_hits: int
    expected_third_misses: int
    expected_third_invalidations: int
    expected_third_writes: int


@dataclass(frozen=True)
class CachedEvaluationSweepTestCase:
    """One invalidating edit and the expected single-generation storage state."""

    description: str
    relative_path: str
    first_source: str
    second_source: str
    expected_first_record_count: int
    expected_second_record_count: int
    expected_shared_keys: int


@dataclass(frozen=True)
class CachedEvaluationDegradationTestCase:
    """One internal cache failure and expected degraded publication stats."""

    description: str
    relative_path: str
    source: str
    expected_misses: int
    expected_writes: int
    expected_non_cacheable: int
    expected_internal_error: bool
    expected_storage_failed: bool
    expected_fault_count: int


@dataclass(frozen=True)
class CachedEvaluationFailureTestCase:
    """Evaluation failure and expected absence of published cache state."""

    description: str
    relative_path: str
    source: str
    expected_error_type: type[Exception]
    expected_cache_exists: bool
