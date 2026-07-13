"""Tests for typed persistent evaluation-result record serialization."""

from __future__ import annotations

import pytest

from strata.analysis.types import ProjectDependencyKind
from strata.cache.fingerprints.models import CacheFingerprint
from strata.cache.fingerprints.types import CanonicalValue
from strata.cache.results._helpers.serialization import (
    fact_from_record,
    fact_to_record,
    file_result_from_record,
    file_result_to_record,
    index_from_record,
    index_to_record,
    metadata_from_record,
    metadata_to_record,
)
from strata.cache.results.constants import (
    CACHE_FACT_KIND,
    CACHE_FILE_RESULT_KIND,
    CACHE_INDEX_KIND,
    CACHE_METADATA_KIND,
)
from strata.cache.results.models import (
    CachedFact,
    CachedFault,
    CachedFileResult,
    CachedRuleExceptionKey,
    CacheIndex,
    CacheIndexEntry,
    CacheMetadata,
    DependencyObservation,
)
from strata.cache.storage._helpers.serialization import decode_cache_record, encode_cache_record
from strata.cache.storage.exceptions import CacheRecordError
from strata.cache.storage.models import CacheRecord
from tests.unit.src.strata.cache.results._test_types import (
    InvalidDependencyRecordTestCase,
    InvalidFileResultRecordTestCase,
    InvalidIndexWriteTestCase,
    TypedRecordRoundTripTestCase,
)

_A_FINGERPRINT: str = "a" * 64
_B_FINGERPRINT: str = "b" * 64
_C_FINGERPRINT: str = "c" * 64


@pytest.mark.parametrize(
    "test_case",
    [
        TypedRecordRoundTripTestCase(
            description="all typed records preserve backend-neutral values",
            metadata=CacheMetadata(global_fingerprint=CacheFingerprint(_A_FINGERPRINT)),
            index=CacheIndex(
                global_fingerprint=CacheFingerprint(_A_FINGERPRINT),
                entries=(
                    CacheIndexEntry(
                        path="src/example.py",
                        source_fingerprint=CacheFingerprint(_B_FINGERPRINT),
                        result_fingerprint=CacheFingerprint(_C_FINGERPRINT),
                        record_fingerprint=CacheFingerprint(_A_FINGERPRINT),
                    ),
                ),
            ),
            file_result=CachedFileResult(
                path="src/example.py",
                source_fingerprint=CacheFingerprint(_B_FINGERPRINT),
                faults=(
                    CachedFault(
                        code="SFA001",
                        path="src/example.py",
                        message="missing annotation",
                        line=4,
                        column=8,
                        remediation="add an annotation",
                    ),
                ),
                applied_exception_keys=(
                    CachedRuleExceptionKey(
                        rule="SFA001",
                        path="src/example.py",
                        symbol="build",
                    ),
                    CachedRuleExceptionKey(
                        rule="SFA002",
                        path="src/example.py",
                        symbol="build",
                    ),
                ),
                dependencies=(
                    DependencyObservation(
                        requester_path="src/example.py",
                        query_path="src/example_types.py",
                        dependency_path="src/example_types.py",
                        kind=ProjectDependencyKind.SOURCE,
                        answer=None,
                    ),
                    DependencyObservation(
                        requester_path="src/example.py",
                        query_path="src/present.py",
                        dependency_path="src/present.py",
                        kind=ProjectDependencyKind.SOURCE,
                        answer=_C_FINGERPRINT,
                    ),
                    DependencyObservation(
                        requester_path="src/example.py",
                        query_path="src/present.py",
                        dependency_path="src/present.py",
                        kind=ProjectDependencyKind.EXISTS,
                        answer=True,
                    ),
                    DependencyObservation(
                        requester_path="src/example.py",
                        query_path="src/present.py",
                        dependency_path="src/present.py",
                        kind=ProjectDependencyKind.IS_FILE,
                        answer=True,
                    ),
                    DependencyObservation(
                        requester_path="src/example.py",
                        query_path="src",
                        dependency_path="src",
                        kind=ProjectDependencyKind.IS_DIR,
                        answer=True,
                    ),
                    DependencyObservation(
                        requester_path="src/example.py",
                        query_path="src/empty",
                        dependency_path="src/empty",
                        kind=ProjectDependencyKind.DIRECTORY_ENTRIES,
                        answer=(),
                    ),
                    DependencyObservation(
                        requester_path="src/example.py",
                        query_path="tests",
                        dependency_path="tests",
                        kind=ProjectDependencyKind.GLOB,
                        answer=("tests/b.py", "tests/a.py"),
                        pattern="*.py",
                        recursive=True,
                    ),
                ),
            ),
            fact=CachedFact(
                path="src/example.py",
                source_fingerprint=CacheFingerprint(_B_FINGERPRINT),
                fact_kind="comments",
                payload=[{"column": 1, "line": 2}],
            ),
            expected_kinds=(
                CACHE_METADATA_KIND,
                CACHE_INDEX_KIND,
                CACHE_FILE_RESULT_KIND,
                CACHE_FACT_KIND,
            ),
            expected_dependency_payload={
                "answer": ["tests/b.py", "tests/a.py"],
                "dependency_path": "tests",
                "kind": "glob",
                "pattern": "*.py",
                "query_path": "tests",
                "recursive": True,
                "requester_path": "src/example.py",
            },
        )
    ],
    ids=lambda case: case.description,
)
def test_given_typed_records_when_round_tripping_storage_then_preserves_contract(
    test_case: TypedRecordRoundTripTestCase,
) -> None:
    records: tuple[CacheRecord, ...] = (
        metadata_to_record(test_case.metadata),
        index_to_record(test_case.index),
        file_result_to_record(test_case.file_result),
        fact_to_record(test_case.fact),
    )
    stored: tuple[CacheRecord | None, ...] = tuple(
        decode_cache_record(data=encode_cache_record(record), expected_kind=record.kind)
        for record in records
    )
    decoded: tuple[object | None, ...] = (
        metadata_from_record(records[0]),
        index_from_record(records[1]),
        file_result_from_record(records[2]),
        fact_from_record(records[3]),
    )

    assert tuple(record.kind for record in records) == test_case.expected_kinds
    assert stored == records
    assert decoded == (test_case.metadata, test_case.index, test_case.file_result, test_case.fact)
    assert isinstance(records[2].payload, dict)
    assert isinstance(records[2].payload["dependencies"], list)
    assert records[2].payload["dependencies"][6] == test_case.expected_dependency_payload


@pytest.mark.parametrize(
    "test_case",
    [
        InvalidFileResultRecordTestCase(
            description="absolute source path is a semantic miss",
            payload={
                "applied_exception_keys": [],
                "dependencies": [],
                "faults": [],
                "path": "/src/example.py",
                "source_fingerprint": _A_FINGERPRINT,
            },
            expected_result=None,
        ),
        InvalidFileResultRecordTestCase(
            description="source query with boolean answer is a semantic miss",
            payload={
                "applied_exception_keys": [],
                "dependencies": [
                    {
                        "answer": False,
                        "dependency_path": "missing.py",
                        "kind": "source",
                        "pattern": None,
                        "query_path": "missing.py",
                        "recursive": False,
                        "requester_path": "src/example.py",
                    }
                ],
                "faults": [],
                "path": "src/example.py",
                "source_fingerprint": _A_FINGERPRINT,
            },
            expected_result=None,
        ),
        InvalidFileResultRecordTestCase(
            description="unsafe aggregate answer path is a semantic miss",
            payload={
                "applied_exception_keys": [],
                "dependencies": [
                    {
                        "answer": ["tests/a.py", "../outside.py"],
                        "dependency_path": "tests",
                        "kind": "directory_entries",
                        "pattern": None,
                        "query_path": "tests",
                        "recursive": False,
                        "requester_path": "src/example.py",
                    }
                ],
                "faults": [],
                "path": "src/example.py",
                "source_fingerprint": _A_FINGERPRINT,
            },
            expected_result=None,
        ),
        InvalidFileResultRecordTestCase(
            description="zero fault line is a semantic miss",
            payload={
                "applied_exception_keys": [],
                "dependencies": [],
                "faults": [
                    {
                        "code": "SFA001",
                        "column": 0,
                        "line": 0,
                        "message": "missing annotation",
                        "path": "src/example.py",
                        "remediation": None,
                    }
                ],
                "path": "src/example.py",
                "source_fingerprint": _A_FINGERPRINT,
            },
            expected_result=None,
        ),
        InvalidFileResultRecordTestCase(
            description="fault column without line is a semantic miss",
            payload={
                "applied_exception_keys": [],
                "dependencies": [],
                "faults": [
                    {
                        "code": "SFA001",
                        "column": 4,
                        "line": None,
                        "message": "missing annotation",
                        "path": "src/example.py",
                        "remediation": None,
                    }
                ],
                "path": "src/example.py",
                "source_fingerprint": _A_FINGERPRINT,
            },
            expected_result=None,
        ),
        InvalidFileResultRecordTestCase(
            description="dependency for another requester is a semantic miss",
            payload={
                "applied_exception_keys": [],
                "dependencies": [
                    {
                        "answer": False,
                        "dependency_path": "missing.py",
                        "kind": "exists",
                        "pattern": None,
                        "query_path": "missing.py",
                        "recursive": False,
                        "requester_path": "src/other.py",
                    }
                ],
                "faults": [],
                "path": "src/example.py",
                "source_fingerprint": _A_FINGERPRINT,
            },
            expected_result=None,
        ),
        InvalidFileResultRecordTestCase(
            description="fault for another file is a semantic miss",
            payload={
                "applied_exception_keys": [],
                "dependencies": [],
                "faults": [
                    {
                        "code": "SFA001",
                        "column": None,
                        "line": None,
                        "message": "missing annotation",
                        "path": "src/other.py",
                        "remediation": None,
                    }
                ],
                "path": "src/example.py",
                "source_fingerprint": _A_FINGERPRINT,
            },
            expected_result=None,
        ),
        InvalidFileResultRecordTestCase(
            description="exception key for another file is a semantic miss",
            payload={
                "applied_exception_keys": [
                    {"path": "src/other.py", "rule": "SFA001", "symbol": "build"}
                ],
                "dependencies": [],
                "faults": [],
                "path": "src/example.py",
                "source_fingerprint": _A_FINGERPRINT,
            },
            expected_result=None,
        ),
        InvalidFileResultRecordTestCase(
            description="unsorted exception keys are a semantic miss",
            payload={
                "applied_exception_keys": [
                    {"path": "src/example.py", "rule": "SFA002", "symbol": "build"},
                    {"path": "src/example.py", "rule": "SFA001", "symbol": "build"},
                ],
                "dependencies": [],
                "faults": [],
                "path": "src/example.py",
                "source_fingerprint": _A_FINGERPRINT,
            },
            expected_result=None,
        ),
        InvalidFileResultRecordTestCase(
            description="malformed exception symbol is a semantic miss",
            payload={
                "applied_exception_keys": [
                    {"path": "src/example.py", "rule": "SFA001", "symbol": "build.inner.deep"}
                ],
                "dependencies": [],
                "faults": [],
                "path": "src/example.py",
                "source_fingerprint": _A_FINGERPRINT,
            },
            expected_result=None,
        ),
        InvalidFileResultRecordTestCase(
            description="unknown file-result field is a semantic miss",
            payload={
                "applied_exception_keys": [],
                "dependencies": [],
                "extra": True,
                "faults": [],
                "path": "src/example.py",
                "source_fingerprint": _A_FINGERPRINT,
            },
            expected_result=None,
        ),
    ],
    ids=lambda case: case.description,
)
def test_given_semantically_invalid_file_record_when_decoding_then_returns_miss(
    test_case: InvalidFileResultRecordTestCase,
) -> None:
    result: CachedFileResult | None = file_result_from_record(
        CacheRecord(kind=CACHE_FILE_RESULT_KIND, payload=test_case.payload)
    )

    assert result == test_case.expected_result


@pytest.mark.parametrize(
    "test_case",
    [
        InvalidDependencyRecordTestCase(
            description="boolean query with string answer is a semantic miss",
            dependency={
                "answer": "yes",
                "dependency_path": "src/example.py",
                "kind": "exists",
                "pattern": None,
                "query_path": "src/example.py",
                "recursive": False,
                "requester_path": "src/example.py",
            },
            expected_result=None,
        ),
        InvalidDependencyRecordTestCase(
            description="directory query with missing answer is a semantic miss",
            dependency={
                "answer": None,
                "dependency_path": "src",
                "kind": "directory_entries",
                "pattern": None,
                "query_path": "src",
                "recursive": False,
                "requester_path": "src/example.py",
            },
            expected_result=None,
        ),
        InvalidDependencyRecordTestCase(
            description="glob query without pattern is a semantic miss",
            dependency={
                "answer": [],
                "dependency_path": "src",
                "kind": "glob",
                "pattern": None,
                "query_path": "src",
                "recursive": False,
                "requester_path": "src/example.py",
            },
            expected_result=None,
        ),
        InvalidDependencyRecordTestCase(
            description="non-glob query with recursion is a semantic miss",
            dependency={
                "answer": False,
                "dependency_path": "src/example.py",
                "kind": "is_file",
                "pattern": None,
                "query_path": "src/example.py",
                "recursive": True,
                "requester_path": "src/example.py",
            },
            expected_result=None,
        ),
    ],
    ids=lambda case: case.description,
)
def test_given_dependency_with_wrong_contract_when_decoding_then_returns_miss(
    test_case: InvalidDependencyRecordTestCase,
) -> None:
    payload: CanonicalValue = {
        "applied_exception_keys": [],
        "dependencies": [test_case.dependency],
        "faults": [],
        "path": "src/example.py",
        "source_fingerprint": _A_FINGERPRINT,
    }
    result: CachedFileResult | None = file_result_from_record(
        CacheRecord(kind=CACHE_FILE_RESULT_KIND, payload=payload)
    )

    assert result == test_case.expected_result


@pytest.mark.parametrize(
    "test_case",
    [
        InvalidIndexWriteTestCase(
            description="unsorted duplicate index paths cannot be serialized",
            index=CacheIndex(
                global_fingerprint=CacheFingerprint(_A_FINGERPRINT),
                entries=(
                    CacheIndexEntry(
                        path="src/b.py",
                        source_fingerprint=CacheFingerprint(_B_FINGERPRINT),
                        result_fingerprint=CacheFingerprint(_C_FINGERPRINT),
                        record_fingerprint=CacheFingerprint(_A_FINGERPRINT),
                    ),
                    CacheIndexEntry(
                        path="src/a.py",
                        source_fingerprint=CacheFingerprint(_B_FINGERPRINT),
                        result_fingerprint=CacheFingerprint(_C_FINGERPRINT),
                        record_fingerprint=CacheFingerprint(_A_FINGERPRINT),
                    ),
                ),
            ),
            expected_error_fragment="entry ordering",
        )
    ],
    ids=lambda case: case.description,
)
def test_given_invalid_typed_index_when_serializing_then_raises_schema_error(
    test_case: InvalidIndexWriteTestCase,
) -> None:
    with pytest.raises(CacheRecordError) as error:
        index_to_record(test_case.index)

    assert test_case.expected_error_fragment in str(error.value)
