"""Content identity for exact encoded cache record bytes."""

from __future__ import annotations

from strata.cache.fingerprints.main.source import fingerprint_source
from strata.cache.fingerprints.models import CacheFingerprint
from strata.cache.storage._helpers.serialization import encode_cache_record
from strata.cache.storage.models import CacheRecord


def record_content_fingerprint(*, record: CacheRecord) -> CacheFingerprint:
    """Return the SHA-256 identity of one record's exact stored bytes."""

    return fingerprint_source(encode_cache_record(record=record))
