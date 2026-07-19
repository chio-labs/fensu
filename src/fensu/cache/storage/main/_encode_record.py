"""Encode one cache record into its exact canonical stored bytes."""

from __future__ import annotations

from fensu.cache.storage._helpers.serialization import encode_cache_record
from fensu.cache.storage.models import CacheRecord


def encode_record(*, record: CacheRecord, payload_is_validated: bool = False) -> bytes:
    """Return the canonical byte encoding persisted for one record."""

    return encode_cache_record(record=record, payload_is_validated=payload_is_validated)
