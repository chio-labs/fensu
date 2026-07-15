"""Encode and validate versioned persistent cache records."""

from __future__ import annotations

import json
import zlib
from typing import Any, cast

from strata.cache.fingerprints.main.source import fingerprint_source
from strata.cache.fingerprints.types import CanonicalValue
from strata.cache.storage.constants import (
    CACHE_RECORD_COMPRESSED_PREFIX,
    CACHE_RECORD_COMPRESSION_LEVEL,
    CACHE_RECORD_COMPRESSION_THRESHOLD,
    CACHE_RECORD_KEYS,
    CACHE_RECORD_KIND_KEY,
    CACHE_RECORD_MAX_DECODED_BYTES,
    CACHE_RECORD_PAYLOAD_KEY,
    CACHE_RECORD_SCHEMA_KEY,
    CACHE_SCHEMA_VERSION,
)
from strata.cache.storage.exceptions import CacheRecordError
from strata.cache.storage.models import CacheRecord


def encode_cache_record(*, record: CacheRecord, payload_is_validated: bool = False) -> bytes:
    """Return canonical JSON bytes for one tagged cache record."""

    canonical_payload: bool = payload_is_validated
    if not canonical_payload:
        try:
            canonical_payload = _is_canonical_value(record.payload)
        except RecursionError as error:
            message: str = "Cache record payload nesting exceeds the schema limit."
            raise CacheRecordError(message) from error
    if not record.kind or not canonical_payload:
        raise CacheRecordError("Cache records require a nonempty kind and canonical payload.")
    value: CanonicalValue = {
        CACHE_RECORD_KIND_KEY: record.kind,
        CACHE_RECORD_PAYLOAD_KEY: record.payload,
        CACHE_RECORD_SCHEMA_KEY: CACHE_SCHEMA_VERSION,
    }
    encoded: bytes = json.dumps(
        value,
        ensure_ascii=True,
        allow_nan=False,
        separators=(",", ":"),
        sort_keys=not payload_is_validated,
    ).encode("utf-8")
    if len(encoded) > CACHE_RECORD_MAX_DECODED_BYTES:
        raise CacheRecordError("Cache record exceeds the decoded size limit.")
    if len(encoded) < CACHE_RECORD_COMPRESSION_THRESHOLD:
        return encoded
    return CACHE_RECORD_COMPRESSED_PREFIX + zlib.compress(
        encoded,
        level=CACHE_RECORD_COMPRESSION_LEVEL,
    )


def decode_cache_record(*, data: bytes, expected_kind: str) -> CacheRecord | None:
    """Return a validated record or None for any unsupported cache data."""

    encoded: bytes | None = _decompressed_record(data)
    if encoded is None:
        return None
    try:
        value: object = json.loads(encoded, parse_float=str, parse_constant=str)
    except (UnicodeDecodeError, json.JSONDecodeError, RecursionError, ValueError):
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
    record: CacheRecord = CacheRecord(
        kind=kind,
        payload=cast(CanonicalValue, payload),
        content_fingerprint=fingerprint_source(data),
    )
    return record if encode_cache_record(record=record, payload_is_validated=True) == data else None


def _decompressed_record(data: bytes) -> bytes | None:
    if not data.startswith(CACHE_RECORD_COMPRESSED_PREFIX):
        return data if len(data) <= CACHE_RECORD_MAX_DECODED_BYTES else None
    compressed: bytes = data[len(CACHE_RECORD_COMPRESSED_PREFIX) :]
    decompressor: Any = zlib.decompressobj()
    try:
        decoded: bytes = decompressor.decompress(
            compressed,
            CACHE_RECORD_MAX_DECODED_BYTES + 1,
        )
    except zlib.error:
        return None
    if (
        len(decoded) > CACHE_RECORD_MAX_DECODED_BYTES
        or decompressor.unconsumed_tail
        or decompressor.unused_data
        or not decompressor.eof
    ):
        return None
    return decoded


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
