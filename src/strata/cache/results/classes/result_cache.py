"""Publish and validate persistent per-file evaluation results."""

from __future__ import annotations

from pathlib import Path

from strata.cache.fingerprints.main.file_result import file_result_fingerprints
from strata.cache.fingerprints.models import CacheFingerprint, FileResultFingerprints
from strata.cache.results.constants import (
    CACHE_FILE_RESULT_KIND,
    CACHE_INDEX_KIND,
    CACHE_INDEX_PATH,
    CACHE_JSON_SUFFIX,
    CACHE_METADATA_KIND,
    CACHE_METADATA_PATH,
    CACHE_RESULTS_DIRECTORY,
    FINGERPRINT_DIRECTORY_PREFIX_LENGTH,
)
from strata.cache.results.helpers.conversion import build_cached_file_result
from strata.cache.results.helpers.dependencies import dependencies_are_current
from strata.cache.results.helpers.serialization import (
    file_result_from_record,
    file_result_to_record,
    index_from_record,
    index_to_record,
    metadata_from_record,
    metadata_to_record,
)
from strata.cache.results.helpers.validation import is_fingerprint
from strata.cache.results.models import (
    CachedFileResult,
    CacheIndex,
    CacheIndexEntry,
    CacheLookup,
    CacheMetadata,
    CacheStats,
)
from strata.cache.storage.main.build_store import build_cache_store
from strata.cache.storage.models import CacheRecord
from strata.cache.storage.types import CacheStorage
from strata.evaluation.core.models import FileEvaluation


class ResultCache:
    """Own typed result publication and integrity-checked loading."""

    def __init__(self, *, repo_root: Path) -> None:
        """Bind a result cache without creating persistent storage."""

        self._repo_root: Path = repo_root.resolve()
        self._store: CacheStorage = build_cache_store(repo_root=self._repo_root)

    def publish(
        self,
        *,
        global_fingerprint: CacheFingerprint,
        evaluations: tuple[FileEvaluation, ...],
    ) -> CacheStats:
        """Publish cacheable file results and an index, returning operation counts."""

        existing_index: CacheIndex | None = self.load_index(global_fingerprint=global_fingerprint)
        existing_entries: dict[str, CacheIndexEntry] = (
            {entry.path: entry for entry in existing_index.entries}
            if existing_index is not None
            else {}
        )
        entries: list[CacheIndexEntry] = []
        writes: int = 0
        non_cacheable: int = 0
        for evaluation in evaluations:
            result: CachedFileResult | None = build_cached_file_result(
                evaluation=evaluation,
                repo_root=self._repo_root,
            )
            if result is None:
                non_cacheable += 1
                continue
            fingerprints: FileResultFingerprints = file_result_fingerprints(
                global_fingerprint=global_fingerprint,
                result=result,
            )
            entry: CacheIndexEntry = CacheIndexEntry(
                path=result.path,
                source_fingerprint=result.source_fingerprint,
                result_fingerprint=fingerprints.result,
                record_fingerprint=fingerprints.record,
            )
            existing_entry: CacheIndexEntry | None = existing_entries.get(result.path)
            if (
                existing_entry == entry
                and self.load_result(
                    global_fingerprint=global_fingerprint,
                    entry=entry,
                )
                is not None
            ):
                entries.append(entry)
                continue
            written: bool = self._store.write(
                relative_path=_result_path(fingerprints.result),
                record=file_result_to_record(result),
            )
            if not written:
                continue
            writes += 1
            entries.append(entry)
        index: CacheIndex = CacheIndex(
            global_fingerprint=global_fingerprint,
            entries=tuple(sorted(entries, key=lambda entry: entry.path)),
        )
        if index == existing_index:
            return CacheStats(
                misses=len(evaluations),
                writes=writes,
                non_cacheable=non_cacheable,
            )
        metadata_written: bool = self._store.write(
            relative_path=CACHE_METADATA_PATH,
            record=metadata_to_record(CacheMetadata(global_fingerprint=global_fingerprint)),
        )
        index_written: bool = False
        if metadata_written:
            index_written = self._store.write(
                relative_path=CACHE_INDEX_PATH,
                record=index_to_record(index),
            )
        return CacheStats(
            misses=len(evaluations),
            writes=writes if index_written else 0,
            non_cacheable=non_cacheable,
        )

    def load_index(self, *, global_fingerprint: CacheFingerprint) -> CacheIndex | None:
        """Return the index only when metadata and index share the active identity."""

        metadata_record: CacheRecord | None = self._store.read(
            relative_path=CACHE_METADATA_PATH,
            expected_kind=CACHE_METADATA_KIND,
        )
        if metadata_record is None:
            return None
        metadata: CacheMetadata | None = metadata_from_record(metadata_record)
        if metadata is None or metadata.global_fingerprint != global_fingerprint:
            return None
        index_record: CacheRecord | None = self._store.read(
            relative_path=CACHE_INDEX_PATH,
            expected_kind=CACHE_INDEX_KIND,
        )
        if index_record is None:
            return None
        index: CacheIndex | None = index_from_record(index_record)
        if index is None or index.global_fingerprint != global_fingerprint:
            return None
        return index

    def load_result(
        self,
        *,
        global_fingerprint: CacheFingerprint,
        entry: CacheIndexEntry,
    ) -> CachedFileResult | None:
        """Return a result only when lookup, correctness, and integrity identities match."""

        if not is_fingerprint(entry.result_fingerprint.value):
            return None
        record: CacheRecord | None = self._store.read(
            relative_path=_result_path(entry.result_fingerprint),
            expected_kind=CACHE_FILE_RESULT_KIND,
        )
        if record is None:
            return None
        result: CachedFileResult | None = file_result_from_record(record)
        if (
            result is None
            or result.path != entry.path
            or result.source_fingerprint != entry.source_fingerprint
        ):
            return None
        fingerprints: FileResultFingerprints = file_result_fingerprints(
            global_fingerprint=global_fingerprint,
            result=result,
        )
        if (
            fingerprints.result != entry.result_fingerprint
            or fingerprints.record != entry.record_fingerprint
        ):
            return None
        return result

    def load_candidate(
        self,
        *,
        global_fingerprint: CacheFingerprint,
        entry: CacheIndexEntry,
        source_fingerprint: CacheFingerprint,
    ) -> CacheLookup:
        """Return an unchanged indexed candidate or an explicit invalidation."""

        if entry.source_fingerprint != source_fingerprint:
            return CacheLookup(result=None, missed=False, invalidated=True)
        result: CachedFileResult | None = self.load_result(
            global_fingerprint=global_fingerprint,
            entry=entry,
        )
        if result is None:
            return CacheLookup(result=None, missed=True, invalidated=False)
        if not dependencies_are_current(
            observations=result.dependencies,
            repo_root=self._repo_root,
        ):
            return CacheLookup(result=None, missed=False, invalidated=True)
        return CacheLookup(result=result, missed=False, invalidated=False)


def _result_path(fingerprint: CacheFingerprint) -> Path:
    value: str = fingerprint.value
    prefix: str = value[:FINGERPRINT_DIRECTORY_PREFIX_LENGTH]
    return CACHE_RESULTS_DIRECTORY / prefix / f"{value}{CACHE_JSON_SUFFIX}"
