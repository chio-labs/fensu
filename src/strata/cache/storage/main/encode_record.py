"""Encode one cache record into its exact canonical stored bytes."""

from __future__ import annotations

from strata.cache.storage._helpers.serialization import encode_cache_record
from strata.cache.storage.models import CacheRecord


def encode_record(*, record: CacheRecord) -> bytes:
    """Return the canonical byte encoding persisted for one record."""

    return encode_cache_record(record)
