"""Typed adapter over native canonical cache-record serialization."""

from __future__ import annotations

from importlib import import_module
from types import ModuleType
from typing import cast

from fensu.cache.fingerprints.models import CacheFingerprint
from fensu.cache.fingerprints.types import CanonicalValue
from fensu.cache.storage.constants import CACHE_RECORD_MAX_DECODED_BYTES
from fensu.cache.storage.exceptions import CacheRecordError
from fensu.cache.storage.models import CacheRecord


def encode_cache_record(*, record: CacheRecord, payload_is_validated: bool = False) -> bytes:
    """Return native canonical bytes for one tagged cache record."""

    try:
        native: ModuleType = import_module("fensu._native")
        return native.cache_encode_record(
            record.kind,
            record.payload,
            payload_is_validated,
            CACHE_RECORD_MAX_DECODED_BYTES,
        )
    except (
        AttributeError,
        ImportError,
        OverflowError,
        RecursionError,
        TypeError,
        ValueError,
    ) as error:
        raise CacheRecordError(str(error)) from error


def decode_cache_record(*, data: bytes, expected_kind: str) -> CacheRecord | None:
    """Return a native-validated record or None for unsupported cache data."""

    try:
        native: ModuleType = import_module("fensu._native")
        row: tuple[str, object, str] | None = native.cache_decode_record(
            data,
            expected_kind,
            CACHE_RECORD_MAX_DECODED_BYTES,
        )
    except (AttributeError, ImportError, OverflowError, RecursionError, TypeError, ValueError):
        return None
    if row is None:
        return None
    return CacheRecord(
        kind=row[0],
        payload=cast(CanonicalValue, row[1]),
        content_fingerprint=CacheFingerprint(value=row[2]),
    )
