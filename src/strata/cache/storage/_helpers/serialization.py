"""Encode and validate versioned persistent cache records."""

from __future__ import annotations

import json
from typing import cast

from strata.cache.fingerprints.main.source import fingerprint_source
from strata.cache.fingerprints.types import CanonicalValue
from strata.cache.storage.constants import (
    CACHE_RECORD_KEYS,
    CACHE_RECORD_KIND_KEY,
    CACHE_RECORD_PAYLOAD_KEY,
    CACHE_RECORD_SCHEMA_KEY,
    CACHE_SCHEMA_VERSION,
)
from strata.cache.storage.exceptions import CacheRecordError
from strata.cache.storage.models import CacheRecord


def encode_cache_record(record: CacheRecord) -> bytes:
    """Return canonical JSON bytes for one tagged cache record."""

    try:
        canonical_payload: bool = _is_canonical_value(record.payload)
    except RecursionError as error:
        raise CacheRecordError("Cache record payload nesting exceeds the schema limit.") from error
    if not record.kind or not canonical_payload:
        raise CacheRecordError("Cache records require a nonempty kind and canonical payload.")
    value: CanonicalValue = {
        CACHE_RECORD_KIND_KEY: record.kind,
        CACHE_RECORD_PAYLOAD_KEY: record.payload,
        CACHE_RECORD_SCHEMA_KEY: CACHE_SCHEMA_VERSION,
    }
    return json.dumps(
        value,
        ensure_ascii=True,
        allow_nan=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")


def decode_cache_record(*, data: bytes, expected_kind: str) -> CacheRecord | None:
    """Return a validated record or None for any unsupported cache data."""

    try:
        value: object = json.loads(data)
    except (UnicodeDecodeError, json.JSONDecodeError, RecursionError):
        return None
    if not isinstance(value, dict) or set(value) != CACHE_RECORD_KEYS:
        return None
    schema_version: object = value.get(CACHE_RECORD_SCHEMA_KEY)
    kind: object = value.get(CACHE_RECORD_KIND_KEY)
    payload: object = value.get(CACHE_RECORD_PAYLOAD_KEY)
    if type(schema_version) is not int or schema_version != CACHE_SCHEMA_VERSION:
        return None
    if not isinstance(kind, str) or not kind or kind != expected_kind:
        return None
    try:
        canonical_payload: bool = _is_canonical_value(payload)
    except RecursionError:
        return None
    if not canonical_payload:
        return None
    record: CacheRecord = CacheRecord(
        kind=kind,
        payload=cast(CanonicalValue, payload),
        content_fingerprint=fingerprint_source(data),
    )
    return record if encode_cache_record(record) == data else None


def _is_canonical_value(value: object) -> bool:
    if value is None or isinstance(value, (bool, int, str)):
        return True
    if isinstance(value, list):
        return all(_is_canonical_value(item) for item in value)
    if isinstance(value, dict):
        return all(
            isinstance(key, str) and _is_canonical_value(item) for key, item in value.items()
        )
    return False
