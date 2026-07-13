"""Publish and validate persistent per-file evaluation results."""

from __future__ import annotations

from pathlib import Path

from strata.cache.fingerprints.main.file_result import file_result_fingerprints
from strata.cache.fingerprints.models import CacheFingerprint, FileResultFingerprints
from strata.cache.results._helpers.conversion import build_cached_file_result
from strata.cache.results._helpers.dependencies import dependencies_are_current
from strata.cache.results._helpers.serialization import (
    file_result_from_record,
    file_result_to_record,
    index_from_record,
    index_to_record,
    metadata_from_record,
    metadata_to_record,
)
from strata.cache.results._helpers.validation import is_fingerprint
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
from strata.cache.results.models import (
    CachedFileResult,
    CacheIndex,
    CacheIndexEntry,
    CacheLookup,
    CacheMetadata,
    CacheStats,
    PublicationCandidate,
    PublicationPreparation,
)
from strata.cache.results.types import DependencyStateCache
from strata.cache.storage.exceptions import CacheRecordError
from strata.cache.storage.main.build_store import build_cache_store
from strata.cache.storage.models import (
    CacheMutation,
    CacheMutationOutcome,
    CacheRead,
    CacheRecord,
    CacheWrite,
)
from strata.cache.storage.types import CacheStorage
from strata.evaluation.models import FileEvaluation


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
        retained_entries: tuple[CacheIndexEntry, ...] = (),
    ) -> CacheStats:
        """Merge, publish, and sweep one complete generation in one transaction."""

        preparation: PublicationPreparation = self._prepare_candidates(
            global_fingerprint=global_fingerprint,
            evaluations=evaluations,
        )
        if not preparation.candidates and self._retained_index_is_current(
            global_fingerprint=global_fingerprint,
            retained_entries=retained_entries,
        ):
            return CacheStats(
                misses=len(evaluations),
                non_cacheable=preparation.non_cacheable,
                internal_error=preparation.internal_error,
            )
        reads: tuple[CacheRead, ...] = (
            CacheRead(relative_path=CACHE_METADATA_PATH, expected_kind=CACHE_METADATA_KIND),
            CacheRead(relative_path=CACHE_INDEX_PATH, expected_kind=CACHE_INDEX_KIND),
            *(
                CacheRead(
                    relative_path=_result_path(candidate.entry.result_fingerprint),
                    expected_kind=CACHE_FILE_RESULT_KIND,
                )
                for candidate in preparation.candidates
            ),
        )
        outcome: CacheMutationOutcome = self._store.mutate_batch(
            reads=reads,
            mutate=lambda records: self._merged_mutation(
                records=records,
                global_fingerprint=global_fingerprint,
                preparation=preparation,
                retained_entries=retained_entries,
            ),
        )
        return CacheStats(
            misses=len(evaluations),
            writes=_result_write_count(outcome.mutation),
            non_cacheable=preparation.non_cacheable,
            storage_failed=not outcome.published,
            internal_error=preparation.internal_error,
        )

    def _prepare_candidates(
        self,
        *,
        global_fingerprint: CacheFingerprint,
        evaluations: tuple[FileEvaluation, ...],
    ) -> PublicationPreparation:
        candidates: list[PublicationCandidate] = []
        non_cacheable: int = 0
        internal_error: bool = False
        for evaluation in evaluations:
            try:
                result: CachedFileResult | None = build_cached_file_result(
                    evaluation=evaluation,
                    repo_root=self._repo_root,
                )
                record: CacheRecord | None = (
                    file_result_to_record(result) if result is not None else None
                )
            except CacheRecordError:
                internal_error = True
                non_cacheable += 1
                continue
            if result is None or record is None:
                non_cacheable += 1
                continue
            fingerprints: FileResultFingerprints = file_result_fingerprints(
                global_fingerprint=global_fingerprint,
                result=result,
            )
            candidates.append(
                PublicationCandidate(
                    entry=CacheIndexEntry(
                        path=result.path,
                        source_fingerprint=result.source_fingerprint,
                        result_fingerprint=fingerprints.result,
                        record_fingerprint=fingerprints.record,
                    ),
                    record=record,
                )
            )
        return PublicationPreparation(
            candidates=tuple(candidates),
            non_cacheable=non_cacheable,
            internal_error=internal_error,
        )

    def _retained_index_is_current(
        self,
        *,
        global_fingerprint: CacheFingerprint,
        retained_entries: tuple[CacheIndexEntry, ...],
    ) -> bool:
        existing_index: CacheIndex | None = self.load_index(global_fingerprint=global_fingerprint)
        if existing_index is None:
            return False
        existing_entries: dict[str, CacheIndexEntry] = {
            entry.path: entry for entry in existing_index.entries
        }
        retained: tuple[CacheIndexEntry, ...] = tuple(
            sorted(
                (
                    existing_entries[entry.path]
                    for entry in retained_entries
                    if entry.path in existing_entries
                ),
                key=lambda entry: entry.path,
            )
        )
        return retained == existing_index.entries

    def _merged_mutation(
        self,
        *,
        records: tuple[CacheRecord | None, ...],
        global_fingerprint: CacheFingerprint,
        preparation: PublicationPreparation,
        retained_entries: tuple[CacheIndexEntry, ...],
    ) -> CacheMutation | None:
        existing_index: CacheIndex | None = _decoded_index(
            metadata_record=records[0],
            index_record=records[1],
            global_fingerprint=global_fingerprint,
        )
        existing_entries: dict[str, CacheIndexEntry] = (
            {entry.path: entry for entry in existing_index.entries}
            if existing_index is not None
            else {}
        )
        entries: list[CacheIndexEntry] = [
            existing_entries[entry.path]
            for entry in retained_entries
            if entry.path in existing_entries
        ]
        writes: list[CacheWrite] = []
        for candidate, record in zip(preparation.candidates, records[2:], strict=True):
            entries.append(candidate.entry)
            if existing_entries.get(candidate.entry.path) == candidate.entry and (
                _validated_result(
                    global_fingerprint=global_fingerprint,
                    entry=candidate.entry,
                    record=record,
                )
                is not None
            ):
                continue
            writes.append(
                CacheWrite(
                    relative_path=_result_path(candidate.entry.result_fingerprint),
                    record=candidate.record,
                )
            )
        index: CacheIndex = CacheIndex(
            global_fingerprint=global_fingerprint,
            entries=tuple(sorted(entries, key=lambda entry: entry.path)),
        )
        if index != existing_index:
            writes.extend(
                (
                    CacheWrite(
                        relative_path=CACHE_METADATA_PATH,
                        record=metadata_to_record(
                            CacheMetadata(global_fingerprint=global_fingerprint)
                        ),
                    ),
                    CacheWrite(
                        relative_path=CACHE_INDEX_PATH,
                        record=index_to_record(index),
                    ),
                )
            )
        if not writes:
            return None
        return CacheMutation(
            writes=tuple(writes),
            swept_prefix=CACHE_RESULTS_DIRECTORY,
            retained_paths=tuple(_result_path(entry.result_fingerprint) for entry in index.entries),
        )

    def load_index(self, *, global_fingerprint: CacheFingerprint) -> CacheIndex | None:
        """Return the index only when metadata and index share the active identity."""

        records: tuple[CacheRecord | None, ...] = self._store.read_batch(
            reads=(
                CacheRead(relative_path=CACHE_METADATA_PATH, expected_kind=CACHE_METADATA_KIND),
                CacheRead(relative_path=CACHE_INDEX_PATH, expected_kind=CACHE_INDEX_KIND),
            )
        )
        return _decoded_index(
            metadata_record=records[0],
            index_record=records[1],
            global_fingerprint=global_fingerprint,
        )

    def load_result(
        self,
        *,
        global_fingerprint: CacheFingerprint,
        entry: CacheIndexEntry,
    ) -> CachedFileResult | None:
        """Return a result only when lookup, correctness, and integrity identities match."""

        record: CacheRecord | None = self._store.read(
            relative_path=_result_path(entry.result_fingerprint),
            expected_kind=CACHE_FILE_RESULT_KIND,
        )
        return _validated_result(
            global_fingerprint=global_fingerprint,
            entry=entry,
            record=record,
        )

    def load_results(
        self,
        *,
        global_fingerprint: CacheFingerprint,
        entries: tuple[CacheIndexEntry, ...],
    ) -> dict[str, CachedFileResult | None]:
        """Load and validate indexed results through one database snapshot."""

        records: tuple[CacheRecord | None, ...] = self._store.read_batch(
            reads=tuple(
                CacheRead(
                    relative_path=_result_path(entry.result_fingerprint),
                    expected_kind=CACHE_FILE_RESULT_KIND,
                )
                for entry in entries
            )
        )
        return {
            entry.path: _validated_result(
                global_fingerprint=global_fingerprint,
                entry=entry,
                record=record,
            )
            for entry, record in zip(entries, records, strict=True)
        }

    def loaded_candidate(
        self,
        *,
        entry: CacheIndexEntry,
        source_fingerprint: CacheFingerprint,
        result: CachedFileResult | None,
        dependency_states: DependencyStateCache,
    ) -> CacheLookup:
        """Return a preloaded unchanged candidate or an explicit invalidation."""

        return self._validate_candidate(
            entry=entry,
            source_fingerprint=source_fingerprint,
            result=result,
            dependency_states=dependency_states,
        )

    def _validate_candidate(
        self,
        *,
        entry: CacheIndexEntry,
        source_fingerprint: CacheFingerprint,
        result: CachedFileResult | None,
        dependency_states: DependencyStateCache | None = None,
    ) -> CacheLookup:
        if entry.source_fingerprint != source_fingerprint:
            return CacheLookup(result=None, missed=False, invalidated=True)
        if result is None:
            return CacheLookup(result=None, missed=True, invalidated=False)
        if not dependencies_are_current(
            observations=result.dependencies,
            repo_root=self._repo_root,
            states=dependency_states,
        ):
            return CacheLookup(result=None, missed=False, invalidated=True)
        return CacheLookup(result=result, missed=False, invalidated=False)

    def load_candidate(
        self,
        *,
        global_fingerprint: CacheFingerprint,
        entry: CacheIndexEntry,
        source_fingerprint: CacheFingerprint,
    ) -> CacheLookup:
        """Return an unchanged indexed candidate or an explicit invalidation."""

        result: CachedFileResult | None = self.load_result(
            global_fingerprint=global_fingerprint,
            entry=entry,
        )
        return self._validate_candidate(
            entry=entry,
            source_fingerprint=source_fingerprint,
            result=result,
        )


def _decoded_index(
    *,
    metadata_record: CacheRecord | None,
    index_record: CacheRecord | None,
    global_fingerprint: CacheFingerprint,
) -> CacheIndex | None:
    if metadata_record is None:
        return None
    metadata: CacheMetadata | None = metadata_from_record(metadata_record)
    if metadata is None or metadata.global_fingerprint != global_fingerprint:
        return None
    if index_record is None:
        return None
    index: CacheIndex | None = index_from_record(index_record)
    if index is None or index.global_fingerprint != global_fingerprint:
        return None
    return index


def _result_write_count(mutation: CacheMutation | None) -> int:
    if mutation is None:
        return 0
    return sum(
        1
        for write in mutation.writes
        if write.relative_path.is_relative_to(CACHE_RESULTS_DIRECTORY)
    )


def _validated_result(
    *,
    global_fingerprint: CacheFingerprint,
    entry: CacheIndexEntry,
    record: CacheRecord | None,
) -> CachedFileResult | None:
    if not is_fingerprint(entry.result_fingerprint.value):
        return None
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


def _result_path(fingerprint: CacheFingerprint) -> Path:
    value: str = fingerprint.value
    prefix: str = value[:FINGERPRINT_DIRECTORY_PREFIX_LENGTH]
    return CACHE_RESULTS_DIRECTORY / prefix / f"{value}{CACHE_JSON_SUFFIX}"
