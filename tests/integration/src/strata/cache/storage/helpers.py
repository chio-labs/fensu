"""Concurrency helpers for persistent cache storage integration tests."""

from __future__ import annotations

from concurrent.futures import Future, ThreadPoolExecutor
from pathlib import Path
from threading import Event

from strata.cache.storage.classes.cache_store import CacheStore
from strata.cache.storage.models import CacheRead, CacheRecord, CacheWrite


def write_records_concurrently(
    *, store: CacheStore, relative_path: Path, kind: str, values: tuple[int, ...]
) -> tuple[bool, ...]:
    """Publish competing complete records to one content path."""

    def write(value: int) -> bool:
        return store.write(
            relative_path=relative_path,
            record=CacheRecord(kind=kind, payload={"value": value}),
        )

    with ThreadPoolExecutor(max_workers=len(values)) as executor:
        futures: list[Future[bool]] = [executor.submit(write, value) for value in values]
    return tuple(future.result() for future in futures)


def read_during_concurrent_writes(
    *, store: CacheStore, relative_path: Path, kind: str, values: tuple[int, ...]
) -> tuple[CacheRecord | None, ...]:
    """Observe one entry while competing writers atomically replace it."""

    finished: Event = Event()
    observed: list[CacheRecord | None] = []

    def read_until_finished() -> None:
        while not finished.is_set():
            observed.append(store.read(relative_path=relative_path, expected_kind=kind))

    with ThreadPoolExecutor(max_workers=len(values) + 1) as executor:
        reader: Future[None] = executor.submit(read_until_finished)
        writers: list[Future[bool]] = [
            executor.submit(
                store.write,
                relative_path=relative_path,
                record=CacheRecord(kind=kind, payload={"value": value}),
            )
            for value in values
        ]
        _ = tuple(writer.result() for writer in writers)
        finished.set()
        _ = reader.result()
    return tuple(observed)


def read_batches_during_concurrent_writes(
    *,
    store: CacheStore,
    relative_paths: tuple[Path, Path],
    kind: str,
    values: tuple[int, ...],
) -> tuple[tuple[CacheRecord | None, ...], ...]:
    """Observe two records while complete transactions replace both."""

    finished: Event = Event()
    observed: list[tuple[CacheRecord | None, ...]] = []
    reads: tuple[CacheRead, ...] = tuple(
        CacheRead(relative_path=path, expected_kind=kind) for path in relative_paths
    )

    def read_until_finished() -> None:
        while not finished.is_set():
            observed.append(store.read_batch(reads=reads))

    def write_batches() -> None:
        for value in values:
            writes: tuple[CacheWrite, ...] = tuple(
                CacheWrite(
                    relative_path=path,
                    record=CacheRecord(kind=kind, payload={"value": value}),
                )
                for path in relative_paths
            )
            _ = store.write_batch(writes=writes)

    with ThreadPoolExecutor(max_workers=2) as executor:
        reader: Future[None] = executor.submit(read_until_finished)
        writer: Future[None] = executor.submit(write_batches)
        _ = writer.result()
        finished.set()
        _ = reader.result()
    return tuple(observed)
