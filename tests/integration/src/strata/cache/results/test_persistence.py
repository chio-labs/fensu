"""Integration tests for typed cache records across store lifetimes."""

from __future__ import annotations

from pathlib import Path

import pytest

from strata.analysis.types import ProjectDependencyKind
from strata.cache.fingerprints.models import CacheFingerprint
from strata.cache.results.constants import CACHE_FILE_RESULT_KIND
from strata.cache.results.helpers.serialization import (
    file_result_from_record,
    file_result_to_record,
)
from strata.cache.results.models import (
    CachedFault,
    CachedFileResult,
    CachedThresholdOverrideUse,
    DependencyObservation,
)
from strata.cache.storage.classes.cache_store import CacheStore
from strata.cache.storage.exceptions import CacheRecordError
from strata.cache.storage.models import CacheRecord
from tests.integration.src.strata.cache.results._test_types import (
    InvalidCachedRuleCodeTestCase,
    PersistentTypedResultTestCase,
)

_SOURCE_FINGERPRINT: str = "d" * 64


@pytest.mark.parametrize(
    "test_case",
    [
        PersistentTypedResultTestCase(
            description="independent stores preserve a complete typed file result",
            relative_path="results/result.json",
            result=CachedFileResult(
                path="src/example.py",
                source_fingerprint=CacheFingerprint(_SOURCE_FINGERPRINT),
                faults=(
                    CachedFault(
                        code="XDB001",
                        path="src/example.py",
                        message="multiline docstring",
                        line=1,
                        column=0,
                    ),
                ),
                applied_exception_keys=(),
                dependencies=(
                    DependencyObservation(
                        requester_path="src/example.py",
                        query_path="src/missing.py",
                        dependency_path="src/missing.py",
                        kind=ProjectDependencyKind.EXISTS,
                        answer=False,
                    ),
                ),
                threshold_override_uses=(
                    CachedThresholdOverrideUse(
                        threshold="max_file_lines",
                        effective_value=3000,
                        matched_pattern="src/**/*.py",
                        reason="Generated clients are wider.",
                        override_order=1,
                        repository_path="src/example.py",
                    ),
                ),
            ),
            expected_write=True,
            expected_result=CachedFileResult(
                path="src/example.py",
                source_fingerprint=CacheFingerprint(_SOURCE_FINGERPRINT),
                faults=(
                    CachedFault(
                        code="XDB001",
                        path="src/example.py",
                        message="multiline docstring",
                        line=1,
                        column=0,
                    ),
                ),
                applied_exception_keys=(),
                dependencies=(
                    DependencyObservation(
                        requester_path="src/example.py",
                        query_path="src/missing.py",
                        dependency_path="src/missing.py",
                        kind=ProjectDependencyKind.EXISTS,
                        answer=False,
                    ),
                ),
                threshold_override_uses=(
                    CachedThresholdOverrideUse(
                        threshold="max_file_lines",
                        effective_value=3000,
                        matched_pattern="src/**/*.py",
                        reason="Generated clients are wider.",
                        override_order=1,
                        repository_path="src/example.py",
                    ),
                ),
            ),
        )
    ],
    ids=lambda case: case.description,
)
def test_given_typed_result_when_reopening_store_then_preserves_complete_result(
    tmp_path: Path,
    test_case: PersistentTypedResultTestCase,
) -> None:
    first_store: CacheStore = CacheStore(repo_root=tmp_path)
    written: bool = first_store.write(
        relative_path=Path(test_case.relative_path),
        record=file_result_to_record(test_case.result),
    )

    second_store: CacheStore = CacheStore(repo_root=tmp_path)
    loaded: CacheRecord | None = second_store.read(
        relative_path=Path(test_case.relative_path),
        expected_kind=CACHE_FILE_RESULT_KIND,
    )
    assert loaded is not None
    decoded: CachedFileResult | None = file_result_from_record(loaded)

    assert written is test_case.expected_write
    assert decoded == test_case.expected_result


@pytest.mark.parametrize(
    "test_case",
    [
        InvalidCachedRuleCodeTestCase(
            description="selector-only core value is rejected in cached fault",
            rule_code="SFR3",
            expected_error_type=CacheRecordError,
        ),
        InvalidCachedRuleCodeTestCase(
            description="selector-only custom namespace is rejected in cached fault",
            rule_code="XDB",
            expected_error_type=CacheRecordError,
        ),
        InvalidCachedRuleCodeTestCase(
            description="legacy hyphenated custom value is rejected in cached fault",
            rule_code="XDB-001",
            expected_error_type=CacheRecordError,
        ),
        InvalidCachedRuleCodeTestCase(
            description="lowercase custom value is rejected in cached fault",
            rule_code="Xdb001",
            expected_error_type=CacheRecordError,
        ),
    ],
    ids=lambda case: case.description,
)
def test_given_invalid_fault_code_when_serializing_cache_then_raises_record_error(
    test_case: InvalidCachedRuleCodeTestCase,
) -> None:
    result: CachedFileResult = CachedFileResult(
        path="src/example.py",
        source_fingerprint=CacheFingerprint(_SOURCE_FINGERPRINT),
        faults=(
            CachedFault(
                code=test_case.rule_code,
                path="src/example.py",
                message="fault",
                line=1,
                column=0,
            ),
        ),
        applied_exception_keys=(),
        dependencies=(),
    )

    with pytest.raises(test_case.expected_error_type):
        file_result_to_record(result)
