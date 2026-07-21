"""Concurrency helper for the native-cache Python boundary."""

from __future__ import annotations

import sqlite3
from collections.abc import Callable
from concurrent.futures import Future, ThreadPoolExecutor
from multiprocessing import get_context
from multiprocessing.context import BaseContext
from multiprocessing.process import BaseProcess
from multiprocessing.synchronize import Event as ProcessEvent
from pathlib import Path

from fensu.cache.storage.classes.cache_store import CacheStore
from fensu.cache.storage.models import CacheRecord


def run_while_database_blocked[T](*, store: CacheStore, operation: Callable[[], T]) -> T:
    """Run one cache operation while another process owns the native write lock."""

    context: BaseContext = get_context("spawn")
    ready: ProcessEvent = context.Event()
    release: ProcessEvent = context.Event()
    blocker: BaseProcess = context.Process(
        target=_hold_database_write_lock,
        args=(store.root, ready, release),
    )
    blocker.start()
    ready.wait()
    try:
        return operation()
    finally:
        release.set()
        blocker.join()


def _hold_database_write_lock(database: Path, ready: ProcessEvent, release: ProcessEvent) -> None:
    with sqlite3.connect(database, isolation_level=None) as blocker:
        blocker.execute("BEGIN IMMEDIATE")
        ready.set()
        release.wait()
        blocker.rollback()


def write_records_concurrently(
    *, store: CacheStore, relative_path: Path, kind: str, values: tuple[int, ...]
) -> tuple[bool, ...]:
    """Publish competing typed Python records through the native adapter."""

    def write(value: int) -> bool:
        return store.write(
            relative_path=relative_path,
            record=CacheRecord(kind=kind, payload={"value": value}),
        )

    with ThreadPoolExecutor(max_workers=len(values)) as executor:
        futures: list[Future[bool]] = [executor.submit(write, value) for value in values]
    return tuple(future.result() for future in futures)
