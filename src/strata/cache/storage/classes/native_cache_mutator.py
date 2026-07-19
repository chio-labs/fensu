"""Adapt typed cache mutations to the native transaction callback."""

from __future__ import annotations

from typing import TYPE_CHECKING

from strata.cache.storage.models import CacheMutation, CacheRecord
from strata.cache.storage.types import CacheMutator

if TYPE_CHECKING:
    from strata.cache.storage.classes.cache_store import CacheStore

type _NativeRecord = tuple[str, object, str]
type _NativeWrite = tuple[str, str, bytes, bool]


class NativeCacheMutator:
    """Retain one typed mutation while returning its native storage shape."""

    def __init__(self, *, store: CacheStore, mutate: CacheMutator) -> None:
        self._store: CacheStore = store
        self._mutate: CacheMutator = mutate
        self.selected: CacheMutation | None = None

    def __call__(
        self,
        rows: list[_NativeRecord | None],
    ) -> tuple[list[_NativeWrite], str | None, list[str], list[str]] | None:
        records: tuple[CacheRecord | None, ...] = tuple(
            self._store.record_from_native(row) for row in rows
        )
        self.selected = self._mutate(records)
        if self.selected is None:
            return None
        encoded: tuple[_NativeWrite, ...] = self._store.encoded_rows(self.selected.writes)
        swept_prefix: str | None = (
            self._store.key(self.selected.swept_prefix)
            if self.selected.swept_prefix is not None
            else None
        )
        retained: list[str] = [self._store.key(path) for path in self.selected.retained_paths]
        deleted: list[str] = [self._store.key(path) for path in self.selected.deleted_paths]
        return list(encoded), swept_prefix, retained, deleted
