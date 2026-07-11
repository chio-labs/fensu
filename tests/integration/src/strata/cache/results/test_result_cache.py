"""Integration tests for indexed persistent file-result publication."""

from __future__ import annotations

from pathlib import Path

import pytest

from strata.cache.fingerprints.models import CacheFingerprint
from strata.cache.results.classes.result_cache import ResultCache
from strata.cache.results.constants import (
    CACHE_JSON_SUFFIX,
    CACHE_RESULTS_DIRECTORY,
    FINGERPRINT_DIRECTORY_PREFIX_LENGTH,
)
from strata.cache.results.helpers.serialization import file_result_to_record
from strata.cache.results.models import (
    CachedFault,
    CachedFileResult,
    CacheIndex,
    CacheIndexEntry,
    CacheLookup,
    CacheStats,
)
from strata.cache.storage.classes.cache_store import CacheStore
from strata.evaluation.core.models import FileEvaluation
from tests.integration.src.strata.cache.results._test_types import (
    ResultCacheCandidateTestCase,
    ResultCacheMissTestCase,
    ResultCachePersistenceTestCase,
    ResultCachePublicationFailureTestCase,
)
from tests.integration.src.strata.cache.results.helpers import (
    external_dependency_evaluation,
    file_evaluation,
    install_cache_write_failure,
)

_GLOBAL_FINGERPRINT: CacheFingerprint = CacheFingerprint("a" * 64)


@pytest.mark.parametrize(
    "test_case",
    [
        ResultCachePersistenceTestCase(
            description="independent repositories load published indexed result",
            relative_path="src/pkg/models.py",
            expected_index_entries=1,
            expected_misses=1,
            expected_writes=1,
            expected_non_cacheable=0,
        )
    ],
    ids=lambda case: case.description,
)
def test_given_file_evaluation_when_publishing_then_new_cache_loads_verified_result(
    tmp_path: Path,
    test_case: ResultCachePersistenceTestCase,
) -> None:
    evaluation: FileEvaluation = file_evaluation(
        repo_root=tmp_path,
        relative_path=test_case.relative_path,
    )
    writer: ResultCache = ResultCache(repo_root=tmp_path)
    stats: CacheStats = writer.publish(
        global_fingerprint=_GLOBAL_FINGERPRINT,
        evaluations=(evaluation,),
    )

    reader: ResultCache = ResultCache(repo_root=tmp_path)
    index: CacheIndex | None = reader.load_index(global_fingerprint=_GLOBAL_FINGERPRINT)
    assert index is not None
    result: CachedFileResult | None = reader.load_result(
        global_fingerprint=_GLOBAL_FINGERPRINT,
        entry=index.entries[0],
    )

    assert len(index.entries) == test_case.expected_index_entries
    assert stats.misses == test_case.expected_misses
    assert stats.writes == test_case.expected_writes
    assert stats.non_cacheable == test_case.expected_non_cacheable
    assert result is not None
    assert result.path == test_case.relative_path


@pytest.mark.parametrize(
    "test_case",
    [
        ResultCachePersistenceTestCase(
            description="unsafe external dependency is omitted from published index",
            relative_path="src/pkg/models.py",
            expected_index_entries=0,
            expected_misses=1,
            expected_writes=0,
            expected_non_cacheable=1,
        )
    ],
    ids=lambda case: case.description,
)
def test_given_non_cacheable_evaluation_when_publishing_then_records_safe_counts(
    tmp_path: Path,
    test_case: ResultCachePersistenceTestCase,
) -> None:
    cache: ResultCache = ResultCache(repo_root=tmp_path)

    stats: CacheStats = cache.publish(
        global_fingerprint=_GLOBAL_FINGERPRINT,
        evaluations=(
            external_dependency_evaluation(
                repo_root=tmp_path,
                relative_path=test_case.relative_path,
            ),
        ),
    )
    index: CacheIndex | None = cache.load_index(global_fingerprint=_GLOBAL_FINGERPRINT)
    assert index is not None

    assert len(index.entries) == test_case.expected_index_entries
    assert stats.misses == test_case.expected_misses
    assert stats.writes == test_case.expected_writes
    assert stats.non_cacheable == test_case.expected_non_cacheable


@pytest.mark.parametrize(
    "test_case",
    [
        ResultCachePublicationFailureTestCase(
            description="transaction failure leaves results and index unpublished",
            relative_path="src/pkg/models.py",
            expected_writes=0,
            expected_index=None,
        ),
    ],
    ids=lambda case: case.description,
)
def test_given_publication_stage_failure_when_publishing_then_reports_no_indexed_writes(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    test_case: ResultCachePublicationFailureTestCase,
) -> None:
    install_cache_write_failure(
        monkeypatch=monkeypatch,
    )
    cache: ResultCache = ResultCache(repo_root=tmp_path)

    stats: CacheStats = cache.publish(
        global_fingerprint=_GLOBAL_FINGERPRINT,
        evaluations=(file_evaluation(repo_root=tmp_path, relative_path=test_case.relative_path),),
    )
    index: CacheIndex | None = cache.load_index(global_fingerprint=_GLOBAL_FINGERPRINT)

    assert stats.writes == test_case.expected_writes
    assert index == test_case.expected_index


@pytest.mark.parametrize(
    "test_case",
    [
        ResultCacheCandidateTestCase(
            description="candidate invalidates on source or observed dependency change",
            relative_path="src/pkg/models.py",
            expected_initial_invalidated=False,
            expected_source_invalidated=True,
            expected_dependency_invalidated=True,
        )
    ],
    ids=lambda case: case.description,
)
def test_given_indexed_candidate_when_inputs_change_then_reports_invalidation(
    tmp_path: Path,
    test_case: ResultCacheCandidateTestCase,
) -> None:
    cache: ResultCache = ResultCache(repo_root=tmp_path)
    _ = cache.publish(
        global_fingerprint=_GLOBAL_FINGERPRINT,
        evaluations=(file_evaluation(repo_root=tmp_path, relative_path=test_case.relative_path),),
    )
    index: CacheIndex | None = cache.load_index(global_fingerprint=_GLOBAL_FINGERPRINT)
    assert index is not None
    entry: CacheIndexEntry = index.entries[0]

    initial: CacheLookup = cache.load_candidate(
        global_fingerprint=_GLOBAL_FINGERPRINT,
        entry=entry,
        source_fingerprint=entry.source_fingerprint,
    )
    source_changed: CacheLookup = cache.load_candidate(
        global_fingerprint=_GLOBAL_FINGERPRINT,
        entry=entry,
        source_fingerprint=CacheFingerprint("d" * 64),
    )
    dependency_path: Path = tmp_path / "src/pkg/dependency.py"
    dependency_path.parent.mkdir(parents=True, exist_ok=True)
    dependency_path.write_text("value = 1\n", encoding="utf-8")
    dependency_changed: CacheLookup = cache.load_candidate(
        global_fingerprint=_GLOBAL_FINGERPRINT,
        entry=entry,
        source_fingerprint=entry.source_fingerprint,
    )

    assert initial.invalidated is test_case.expected_initial_invalidated
    assert initial.result is not None
    assert source_changed.invalidated is test_case.expected_source_invalidated
    assert source_changed.result is None
    assert dependency_changed.invalidated is test_case.expected_dependency_invalidated
    assert dependency_changed.result is None


@pytest.mark.parametrize(
    "test_case",
    [
        ResultCacheMissTestCase(
            description="different global identity rejects complete index",
            relative_path="src/pkg/models.py",
            expected_result=None,
        )
    ],
    ids=lambda case: case.description,
)
def test_given_different_global_identity_when_loading_index_then_returns_miss(
    tmp_path: Path,
    test_case: ResultCacheMissTestCase,
) -> None:
    cache: ResultCache = ResultCache(repo_root=tmp_path)
    _ = cache.publish(
        global_fingerprint=_GLOBAL_FINGERPRINT,
        evaluations=(file_evaluation(repo_root=tmp_path, relative_path=test_case.relative_path),),
    )

    index: CacheIndex | None = cache.load_index(
        global_fingerprint=CacheFingerprint("c" * 64),
    )

    assert index == test_case.expected_result


@pytest.mark.parametrize(
    "test_case",
    [
        ResultCacheMissTestCase(
            description="valid JSON diagnostic mutation fails record integrity",
            relative_path="src/pkg/models.py",
            expected_result=None,
            expected_missed=True,
            expected_invalidated=False,
        )
    ],
    ids=lambda case: case.description,
)
def test_given_semantically_valid_result_corruption_when_loading_then_returns_miss(
    tmp_path: Path,
    test_case: ResultCacheMissTestCase,
) -> None:
    cache: ResultCache = ResultCache(repo_root=tmp_path)
    _ = cache.publish(
        global_fingerprint=_GLOBAL_FINGERPRINT,
        evaluations=(file_evaluation(repo_root=tmp_path, relative_path=test_case.relative_path),),
    )
    index: CacheIndex | None = cache.load_index(global_fingerprint=_GLOBAL_FINGERPRINT)
    assert index is not None
    entry: CacheIndexEntry = index.entries[0]
    loaded: CachedFileResult | None = cache.load_result(
        global_fingerprint=_GLOBAL_FINGERPRINT,
        entry=entry,
    )
    assert loaded is not None
    corrupted: CachedFileResult = CachedFileResult(
        path=loaded.path,
        source_fingerprint=loaded.source_fingerprint,
        faults=(
            CachedFault(
                code=loaded.faults[0].code,
                path=loaded.path,
                message="corrupted diagnostic",
                line=loaded.faults[0].line,
                column=loaded.faults[0].column,
            ),
        ),
        applied_exception_keys=loaded.applied_exception_keys,
        dependencies=loaded.dependencies,
    )
    value: str = entry.result_fingerprint.value
    relative_path: Path = (
        CACHE_RESULTS_DIRECTORY
        / value[:FINGERPRINT_DIRECTORY_PREFIX_LENGTH]
        / f"{value}{CACHE_JSON_SUFFIX}"
    )
    store: CacheStore = CacheStore(repo_root=tmp_path)
    written: bool = store.write(
        relative_path=relative_path,
        record=file_result_to_record(corrupted),
    )

    result: CachedFileResult | None = cache.load_result(
        global_fingerprint=_GLOBAL_FINGERPRINT,
        entry=entry,
    )
    candidate: CacheLookup = cache.load_candidate(
        global_fingerprint=_GLOBAL_FINGERPRINT,
        entry=entry,
        source_fingerprint=entry.source_fingerprint,
    )

    assert written is True
    assert result == test_case.expected_result
    assert candidate.missed is test_case.expected_missed
    assert candidate.invalidated is test_case.expected_invalidated
