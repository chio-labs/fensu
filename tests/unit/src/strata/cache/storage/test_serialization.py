"""Tests for versioned cache record serialization."""

from __future__ import annotations

import zlib

import pytest

import strata.cache.storage._helpers.serialization as serialization_module
from strata.cache.storage._helpers.serialization import decode_cache_record, encode_cache_record
from strata.cache.storage.constants import CACHE_RECORD_COMPRESSED_PREFIX
from strata.cache.storage.exceptions import CacheRecordError
from strata.cache.storage.models import CacheRecord
from tests.unit.src.strata.cache.storage._test_types import (
    BoundedCompressedCacheRecordTestCase,
    CacheRecordRoundTripTestCase,
    CompressedCacheRecordTestCase,
    InvalidCacheRecordTestCase,
    InvalidCacheRecordWriteTestCase,
)
from tests.unit.src.strata.cache.storage.helpers import deeply_nested_cache_json


@pytest.mark.parametrize(
    "test_case",
    [
        CacheRecordRoundTripTestCase(
            description="record encoding is canonical and round trips",
            kind="metadata",
            payload={"zeta": [2, 1], "alpha": True},
            expected_bytes=(
                b'{"kind":"metadata","payload":{"alpha":true,"zeta":[2,1]},"schema_version":4}'
            ),
        )
    ],
    ids=lambda case: case.description,
)
def test_given_cache_record_when_encoding_then_round_trips_canonical_bytes(
    test_case: CacheRecordRoundTripTestCase,
) -> None:
    record: CacheRecord = CacheRecord(kind=test_case.kind, payload=test_case.payload)

    encoded: bytes = encode_cache_record(record=record)
    decoded: CacheRecord | None = decode_cache_record(data=encoded, expected_kind=test_case.kind)

    assert encoded == test_case.expected_bytes
    assert decoded == record


@pytest.mark.parametrize(
    "test_case",
    [
        CompressedCacheRecordTestCase(
            description="large canonical payload uses deterministic compressed framing",
            payload_size=10_000,
            expected_prefix=CACHE_RECORD_COMPRESSED_PREFIX,
            expected_smaller=True,
        )
    ],
    ids=lambda case: case.description,
)
def test_given_large_cache_record_when_encoding_then_compresses_and_round_trips(
    test_case: CompressedCacheRecordTestCase,
) -> None:
    record: CacheRecord = CacheRecord(
        kind="file_result",
        payload={"source": "a" * test_case.payload_size},
    )
    encoded: bytes = encode_cache_record(record=record)
    decoded: CacheRecord | None = decode_cache_record(data=encoded, expected_kind=record.kind)

    assert encoded.startswith(test_case.expected_prefix)
    assert (len(encoded) < test_case.payload_size) is test_case.expected_smaller
    assert decoded == record


@pytest.mark.parametrize(
    "test_case",
    [
        BoundedCompressedCacheRecordTestCase(
            description="compressed expansion beyond the configured limit is a cache miss",
            decoded_limit=64,
            payload_size=65,
            expected_record=None,
        )
    ],
    ids=lambda case: case.description,
)
def test_given_oversized_compressed_record_when_decoding_then_returns_miss(
    monkeypatch: pytest.MonkeyPatch,
    test_case: BoundedCompressedCacheRecordTestCase,
) -> None:
    monkeypatch.setattr(
        serialization_module,
        "CACHE_RECORD_MAX_DECODED_BYTES",
        test_case.decoded_limit,
    )
    encoded: bytes = CACHE_RECORD_COMPRESSED_PREFIX + zlib.compress(b"a" * test_case.payload_size)

    decoded: CacheRecord | None = decode_cache_record(
        data=encoded,
        expected_kind="file_result",
    )

    assert decoded is test_case.expected_record


@pytest.mark.parametrize(
    "test_case",
    [
        InvalidCacheRecordTestCase(
            description="truncated JSON is a cache miss",
            data=b'{"kind":"metadata"',
            expected_kind="metadata",
            expected_record=None,
        ),
        InvalidCacheRecordTestCase(
            description="unsupported schema is a cache miss",
            data=b'{"kind":"metadata","payload":{},"schema_version":5}',
            expected_kind="metadata",
            expected_record=None,
        ),
        InvalidCacheRecordTestCase(
            description="wrong record kind is a cache miss",
            data=b'{"kind":"index","payload":{},"schema_version":1}',
            expected_kind="metadata",
            expected_record=None,
        ),
        InvalidCacheRecordTestCase(
            description="noncanonical floating payload is a cache miss",
            data=b'{"kind":"metadata","payload":1.5,"schema_version":4}',
            expected_kind="metadata",
            expected_record=None,
        ),
        InvalidCacheRecordTestCase(
            description="unknown envelope field is a cache miss",
            data=(b'{"extra":true,"kind":"metadata","payload":{},"schema_version":1}'),
            expected_kind="metadata",
            expected_record=None,
        ),
        InvalidCacheRecordTestCase(
            description="noncanonical whitespace is a cache miss",
            data=b'{"kind": "metadata", "payload": {}, "schema_version": 1}',
            expected_kind="metadata",
            expected_record=None,
        ),
        InvalidCacheRecordTestCase(
            description="duplicate envelope keys are a cache miss",
            data=(b'{"kind":"index","kind":"metadata","payload":{},"schema_version":1}'),
            expected_kind="metadata",
            expected_record=None,
        ),
        InvalidCacheRecordTestCase(
            description="adversarial nesting is a cache miss",
            data=deeply_nested_cache_json(2000),
            expected_kind="metadata",
            expected_record=None,
        ),
        InvalidCacheRecordTestCase(
            description="oversized JSON integer conversion is a cache miss",
            data=(b'{"kind":"metadata","payload":' + (b"9" * 5_000) + b',"schema_version":4}'),
            expected_kind="metadata",
            expected_record=None,
        ),
    ],
    ids=lambda case: case.description,
)
def test_given_unsupported_cache_bytes_when_decoding_then_returns_miss(
    test_case: InvalidCacheRecordTestCase,
) -> None:
    record: CacheRecord | None = decode_cache_record(
        data=test_case.data,
        expected_kind=test_case.expected_kind,
    )

    assert record == test_case.expected_record


@pytest.mark.parametrize(
    "test_case",
    [
        InvalidCacheRecordWriteTestCase(
            description="empty record kind cannot be serialized",
            kind="",
            expected_error_fragment="nonempty kind and canonical payload",
        )
    ],
    ids=lambda case: case.description,
)
def test_given_invalid_cache_record_when_encoding_then_raises_schema_error(
    test_case: InvalidCacheRecordWriteTestCase,
) -> None:
    with pytest.raises(CacheRecordError) as error:
        encode_cache_record(record=CacheRecord(kind=test_case.kind, payload={}))

    assert test_case.expected_error_fragment in str(error.value)
