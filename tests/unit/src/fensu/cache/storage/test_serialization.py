"""Python conversion boundaries for native cache records."""

from __future__ import annotations

from typing import cast

import pytest

from fensu.cache.fingerprints.types import CanonicalValue
from fensu.cache.storage._helpers.serialization import decode_cache_record, encode_cache_record
from fensu.cache.storage.exceptions import CacheRecordError
from fensu.cache.storage.models import CacheRecord
from tests.unit.src.fensu.cache.storage._test_types import (
    InvalidSerializationBoundaryTestCase,
    SerializationBoundaryTestCase,
)


@pytest.mark.parametrize(
    "test_case",
    [
        SerializationBoundaryTestCase(
            description="Python containers convert to canonical native bytes and back",
            kind="metadata",
            payload={"zeta": [2, 1], "alpha": True},
            expected_bytes=b'{"kind":"metadata","payload":{"alpha":true,"zeta":[2,1]},"schema_version":4}',
        )
    ],
    ids=lambda case: case.description,
)
def test_given_python_payload_when_serializing_then_crosses_native_boundary(
    test_case: SerializationBoundaryTestCase,
) -> None:
    record: CacheRecord = CacheRecord(kind=test_case.kind, payload=test_case.payload)

    encoded: bytes = encode_cache_record(record=record)
    decoded: CacheRecord | None = decode_cache_record(data=encoded, expected_kind=test_case.kind)

    assert encoded == test_case.expected_bytes
    assert decoded == record


@pytest.mark.parametrize(
    "test_case",
    [
        InvalidSerializationBoundaryTestCase(
            description="unsupported Python objects raise the typed adapter error",
            payload=object(),
            expected_error_fragment="nonempty kind and canonical payload",
        )
    ],
    ids=lambda case: case.description,
)
def test_given_unsupported_python_payload_when_serializing_then_raises_typed_error(
    test_case: InvalidSerializationBoundaryTestCase,
) -> None:
    with pytest.raises(CacheRecordError) as error:
        encode_cache_record(
            record=CacheRecord(
                kind="metadata",
                payload=cast(CanonicalValue, test_case.payload),
            )
        )

    assert test_case.expected_error_fragment in str(error.value)
