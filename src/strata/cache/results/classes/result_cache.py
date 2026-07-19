"""Native persistent evaluation-generation boundary."""

from importlib import import_module
from pathlib import Path
from types import ModuleType

from strata.cache.fingerprints.models import CacheFingerprint
from strata.cache.results._helpers.conversion import (
    native_evaluation_payload,
    restore_native_contribution,
    restore_native_evaluation,
)
from strata.cache.results.models import (
    CachedCheckOutput,
    CacheIndexEntry,
    CacheStats,
    NativeGenerationPlan,
)
from strata.evaluation.models import FileEvaluation


class ResultCache:
    """Expose fail-soft native generation operations to check orchestration."""

    def __init__(self, *, repo_root: Path) -> None:
        """Bind a result cache without creating persistent storage."""

        self._repo_root: Path = repo_root.resolve()

    def load_native_replay(
        self,
        *,
        global_fingerprint: CacheFingerprint,
        targets: tuple[str, ...],
        source_fingerprints: dict[str, CacheFingerprint | None],
    ) -> CachedCheckOutput | None:
        """Return a fully native-validated rendered generation when current."""

        from strata.cache.storage.classes.cache_store import _record_metrics
        from strata.cache.storage.constants import CACHE_RECORD_MAX_DECODED_BYTES

        try:
            native: ModuleType = import_module("strata._native")
            row, metrics = native.cache_replay_generation(
                self._repo_root,
                global_fingerprint.value,
                [(path, _fingerprint_value(source_fingerprints.get(path))) for path in targets],
                CACHE_RECORD_MAX_DECODED_BYTES,
            )
        except (AttributeError, ImportError, OSError, RuntimeError, TypeError, ValueError):
            return None
        _record_metrics(metrics)
        if row is None:
            return None
        _record_native_observation()
        return CachedCheckOutput(
            global_fingerprint=global_fingerprint,
            index_fingerprint=CacheFingerprint(value=row[4]),
            targets=tuple(row[0]),
            plain_output=row[1],
            color_output=row[2],
            exit_code=row[3],
        )

    def plan_native_generation(
        self,
        *,
        global_fingerprint: CacheFingerprint,
        targets: tuple[str, ...],
        source_fingerprints: dict[str, CacheFingerprint | None],
        allow_edit: bool = True,
    ) -> NativeGenerationPlan | None:
        """Return Rust-validated replay inputs and complete per-target miss decisions."""

        from strata.cache.storage.classes.cache_store import _record_metrics
        from strata.cache.storage.constants import CACHE_RECORD_MAX_DECODED_BYTES

        try:
            native: ModuleType = import_module("strata._native")
            row, metrics = native.cache_plan_generation(
                self._repo_root,
                global_fingerprint.value,
                [(path, _fingerprint_value(source_fingerprints.get(path))) for path in targets],
                allow_edit,
                CACHE_RECORD_MAX_DECODED_BYTES,
            )
        except (AttributeError, ImportError, OSError, RuntimeError, TypeError, ValueError):
            return None
        _record_metrics(metrics)
        if row is None:
            return None
        entries: tuple[CacheIndexEntry, ...] = tuple(
            CacheIndexEntry(
                path=value[0],
                source_fingerprint=CacheFingerprint(value[1]),
                result_fingerprint=CacheFingerprint(value[2]),
                record_fingerprint=CacheFingerprint(value[3]),
            )
            for value in row[2]
        )
        entries_by_path: dict[str, CacheIndexEntry] = {entry.path: entry for entry in entries}
        try:
            cached_evaluations: tuple[FileEvaluation, ...] = tuple(
                restore_native_evaluation(payload=payload, repo_root=self._repo_root)
                for payload in row[3]
            )
            retained_evaluations: tuple[FileEvaluation, ...] = tuple(
                restore_native_contribution(
                    payload=payload,
                    source_fingerprint=entries_by_path[str(payload["path"])].source_fingerprint,
                    repo_root=self._repo_root,
                )
                for payload in row[4]
            )
        except (KeyError, TypeError, ValueError):
            return None
        return NativeGenerationPlan(
            mode=row[0],
            index_fingerprint=(CacheFingerprint(row[1]) if row[1] is not None else None),
            retained_entries=entries,
            cached_evaluations=cached_evaluations,
            retained_evaluations=retained_evaluations,
            miss_paths=tuple(row[5]),
            hits=row[6],
            misses=row[7],
            invalidations=row[8],
        )

    def publish_native_generation(
        self,
        *,
        global_fingerprint: CacheFingerprint,
        evaluations: tuple[FileEvaluation, ...],
        retained_entries: tuple[CacheIndexEntry, ...],
        expected_index_fingerprint: CacheFingerprint | None,
        retain_all_observations: bool,
    ) -> CacheStats:
        """Publish one complete generation through a Rust-owned transaction."""

        from strata.cache.storage.classes.cache_store import _record_metrics
        from strata.cache.storage.constants import CACHE_RECORD_MAX_DECODED_BYTES

        payloads: list[dict[str, object] | None] = [
            native_evaluation_payload(evaluation=evaluation, repo_root=self._repo_root)
            for evaluation in evaluations
        ]
        try:
            native: ModuleType = import_module("strata._native")
            row, metrics = native.cache_publish_generation(
                self._repo_root,
                global_fingerprint.value,
                _fingerprint_value(expected_index_fingerprint),
                [
                    (
                        entry.path,
                        entry.source_fingerprint.value,
                        entry.result_fingerprint.value,
                        entry.record_fingerprint.value,
                    )
                    for entry in retained_entries
                ],
                payloads,
                (retain_all_observations, CACHE_RECORD_MAX_DECODED_BYTES),
            )
        except (AttributeError, ImportError, OSError, RuntimeError, TypeError, ValueError):
            return CacheStats(storage_failed=True, internal_error=True)
        _record_metrics(metrics)
        return CacheStats(
            misses=len(evaluations),
            writes=row[0],
            non_cacheable=row[1],
            storage_failed=row[2],
            internal_error=row[3],
            index_fingerprint=CacheFingerprint(row[4]) if row[4] is not None else None,
        )

    def store_check_output(
        self,
        *,
        global_fingerprint: CacheFingerprint,
        targets: tuple[str, ...],
        plain_output: str,
        color_output: str,
        exit_code: int,
        expected_index_fingerprint: CacheFingerprint,
    ) -> bool:
        """Bind one rendered check surface to the current native generation."""

        from strata.cache.storage.classes.cache_store import _record_metrics
        from strata.cache.storage.constants import CACHE_RECORD_MAX_DECODED_BYTES

        try:
            native: ModuleType = import_module("strata._native")
            stored, metrics = native.cache_store_check_output(
                self._repo_root,
                global_fingerprint.value,
                expected_index_fingerprint.value,
                (sorted(targets), plain_output, color_output, exit_code),
                CACHE_RECORD_MAX_DECODED_BYTES,
            )
        except (AttributeError, ImportError, OSError, RuntimeError, TypeError, ValueError):
            return False
        _record_metrics(metrics)
        return stored


def _fingerprint_value(fingerprint: CacheFingerprint | None) -> str | None:
    return fingerprint.value if fingerprint is not None else None


def _record_native_observation() -> None:
    from strata.instrumentation.constants import (
        OPERATION_COUNTERS,
        PROJECT_QUERY_OBSERVATION_OPERATION,
    )

    OPERATION_COUNTERS.record(operation=PROJECT_QUERY_OBSERVATION_OPERATION)
