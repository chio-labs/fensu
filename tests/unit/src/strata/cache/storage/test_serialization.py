"""Tests for versioned cache record serialization."""

from __future__ import annotations

import pytest

from strata.cache.storage._helpers.serialization import decode_cache_record, encode_cache_record
from strata.cache.storage.exceptions import CacheRecordError
from strata.cache.storage.models import CacheRecord
from tests.unit.src.strata.cache.storage._test_types import (
    CacheRecordRoundTripTestCase,
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
                b'{"kind":"metadata","payload":{"alpha":true,"zeta":[2,1]},"schema_version":2}'
            ),
        )
    ],
    ids=lambda case: case.description,
)
def test_given_cache_record_when_encoding_then_round_trips_canonical_bytes(
    test_case: CacheRecordRoundTripTestCase,
) -> None:
    record: CacheRecord = CacheRecord(kind=test_case.kind, payload=test_case.payload)

    encoded: bytes = encode_cache_record(record)
    decoded: CacheRecord | None = decode_cache_record(data=encoded, expected_kind=test_case.kind)

    assert encoded == test_case.expected_bytes
    assert decoded == record


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
            data=b'{"kind":"metadata","payload":{},"schema_version":3}',
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
            data=b'{"kind":"metadata","payload":1.5,"schema_version":1}',
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
        encode_cache_record(CacheRecord(kind=test_case.kind, payload={}))

    assert test_case.expected_error_fragment in str(error.value)
