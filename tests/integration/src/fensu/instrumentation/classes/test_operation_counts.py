"""Deterministic operation-count invariants over a generated corpus."""

from __future__ import annotations

from pathlib import Path

import pytest

from fensu.instrumentation.constants import (
    CACHE_MANIFEST_VALIDATION_OPERATION,
    CACHE_RECORD_BYTES_READ_OPERATION,
    CACHE_RECORD_DELETE_OPERATION,
    CACHE_RECORD_READ_OPERATION,
    CACHE_RECORD_SCAN_OPERATION,
    CANONICAL_ENCODE_OPERATION,
    DEPENDENCY_RECORD_OPERATION,
    FRESH_EVALUATION_OPERATION,
    PARSE_OPERATION,
    PHASE_CACHE_EVALUATION_NANOSECONDS,
    PHASE_DISCOVERY_NANOSECONDS,
    PHASE_FULL_EVALUATION_NANOSECONDS,
    PHASE_GLOBAL_FINGERPRINT_NANOSECONDS,
    PROJECT_QUERY_CACHE_HIT_OPERATION,
    PROJECT_QUERY_CACHE_MISS_OPERATION,
    PROJECT_QUERY_DIRECTORY_ENTRIES_OPERATION,
    PROJECT_QUERY_EXISTS_OPERATION,
    PROJECT_QUERY_GLOB_OPERATION,
    PROJECT_QUERY_IS_DIR_OPERATION,
    PROJECT_QUERY_IS_FILE_OPERATION,
    PROJECT_QUERY_OBSERVATION_OPERATION,
    PROJECT_QUERY_PYTHON_ANCHOR_OPERATION,
    PROJECT_QUERY_SOURCE_OPERATION,
    RELATIVE_PATH_COMPUTE_OPERATION,
)
from scripts.perfcorpus.main.generate_corpus import generate_corpus
from scripts.perfcorpus.models import CorpusSpec
from tests.integration.src.fensu.instrumentation.classes._test_types import (
    CachedCountsTestCase,
    ChurnCountsTestCase,
    EditCountsTestCase,
    UncachedCountsTestCase,
)
from tests.integration.src.fensu.instrumentation.classes.helpers import (
    append_source_newlines,
    appended_module_constant,
    counted_check,
    python_file_count,
)

_MAX_PARSES_PER_FILE: int = 2
_MAX_RELATIVE_COMPUTES_PER_FILE: int = 4
_MAX_CANONICAL_ENCODES_PER_FILE: int = 4
_MAX_DEPENDENCY_RECORDS_PER_FILE: int = 12
_MAX_WARM_CANONICAL_ENCODES: int = 8


@pytest.mark.parametrize(
    "test_case",
    [
        UncachedCountsTestCase(
            description="native uncached checks stay linear and never touch cache paths",
            file_target=120,
            seed=0,
            expected_relative_path_computes=0,
            expected_min_discovery_nanoseconds=1,
            expected_min_full_evaluation_nanoseconds=1,
            expected_min_query_cache_hits=1,
            expected_min_query_cache_misses=1,
        )
    ],
    ids=lambda case: case.description,
)
def test_given_uncached_check_when_counting_then_operations_stay_linear(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    test_case: UncachedCountsTestCase,
) -> None:
    _ = generate_corpus(
        spec=CorpusSpec(target=tmp_path, file_target=test_case.file_target, seed=test_case.seed)
    )
    files: int = python_file_count(root=tmp_path)
    monkeypatch.chdir(tmp_path)
    counts: dict[str, int] = counted_check(argv=("--no-color", "--no-cache"))

    assert counts.get(RELATIVE_PATH_COMPUTE_OPERATION, 0) == (
        test_case.expected_relative_path_computes
    )
    assert counts[FRESH_EVALUATION_OPERATION] == files
    assert counts.get(PARSE_OPERATION, 0) <= files * _MAX_PARSES_PER_FILE
    assert counts[DEPENDENCY_RECORD_OPERATION] <= files * _MAX_DEPENDENCY_RECORDS_PER_FILE
    assert counts[PHASE_DISCOVERY_NANOSECONDS] >= test_case.expected_min_discovery_nanoseconds
    assert counts[PHASE_FULL_EVALUATION_NANOSECONDS] >= (
        test_case.expected_min_full_evaluation_nanoseconds
    )
    assert counts[PROJECT_QUERY_CACHE_HIT_OPERATION] >= test_case.expected_min_query_cache_hits
    assert counts[PROJECT_QUERY_CACHE_MISS_OPERATION] >= test_case.expected_min_query_cache_misses
    query_kind_observations: int = sum(
        counts.get(operation, 0)
        for operation in (
            PROJECT_QUERY_SOURCE_OPERATION,
            PROJECT_QUERY_EXISTS_OPERATION,
            PROJECT_QUERY_IS_FILE_OPERATION,
            PROJECT_QUERY_IS_DIR_OPERATION,
            PROJECT_QUERY_DIRECTORY_ENTRIES_OPERATION,
            PROJECT_QUERY_GLOB_OPERATION,
            PROJECT_QUERY_PYTHON_ANCHOR_OPERATION,
        )
    )
    assert query_kind_observations == counts[PROJECT_QUERY_OBSERVATION_OPERATION]


@pytest.mark.parametrize(
    "test_case",
    [
        CachedCountsTestCase(
            description="native warm checks restore every file without parsing",
            file_target=120,
            seed=0,
            expected_warm_fresh_evaluations=0,
            expected_warm_parses=0,
            expected_warm_manifest_validations=1,
            expected_min_warm_cache_bytes_read=1,
            expected_min_warm_query_observations=1,
            expected_min_warm_fingerprint_nanoseconds=1,
            expected_min_warm_cache_evaluation_nanoseconds=1,
        )
    ],
    ids=lambda case: case.description,
)
def test_given_cold_then_warm_check_when_counting_then_warm_run_stays_pure(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    test_case: CachedCountsTestCase,
) -> None:
    _ = generate_corpus(
        spec=CorpusSpec(target=tmp_path, file_target=test_case.file_target, seed=test_case.seed)
    )
    files: int = python_file_count(root=tmp_path)
    monkeypatch.chdir(tmp_path)
    cold_counts: dict[str, int] = counted_check(argv=("--no-color", "--cache"))
    warm_counts: dict[str, int] = counted_check(argv=("--no-color", "--cache"))

    assert cold_counts[FRESH_EVALUATION_OPERATION] == files
    assert cold_counts[RELATIVE_PATH_COMPUTE_OPERATION] <= files * _MAX_RELATIVE_COMPUTES_PER_FILE
    assert cold_counts[CANONICAL_ENCODE_OPERATION] <= files * _MAX_CANONICAL_ENCODES_PER_FILE
    assert warm_counts.get(FRESH_EVALUATION_OPERATION, 0) == (
        test_case.expected_warm_fresh_evaluations
    )
    assert warm_counts.get(PARSE_OPERATION, 0) == test_case.expected_warm_parses
    assert warm_counts.get(CACHE_MANIFEST_VALIDATION_OPERATION, 0) == (
        test_case.expected_warm_manifest_validations
    )
    assert warm_counts.get(CACHE_RECORD_BYTES_READ_OPERATION, 0) >= (
        test_case.expected_min_warm_cache_bytes_read
    )
    assert warm_counts.get(PROJECT_QUERY_OBSERVATION_OPERATION, 0) >= (
        test_case.expected_min_warm_query_observations
    )
    assert warm_counts.get(PHASE_GLOBAL_FINGERPRINT_NANOSECONDS, 0) >= (
        test_case.expected_min_warm_fingerprint_nanoseconds
    )
    assert warm_counts.get(PHASE_CACHE_EVALUATION_NANOSECONDS, 0) >= (
        test_case.expected_min_warm_cache_evaluation_nanoseconds
    )
    assert warm_counts.get(RELATIVE_PATH_COMPUTE_OPERATION, 0) <= (
        files * _MAX_RELATIVE_COMPUTES_PER_FILE
    )
    assert warm_counts.get(CANONICAL_ENCODE_OPERATION, 0) <= _MAX_WARM_CANONICAL_ENCODES


@pytest.mark.parametrize(
    "test_case",
    [
        EditCountsTestCase(
            description="native one edited file re-evaluates without CPython parsing",
            file_target=120,
            seed=0,
            expected_fresh_evaluations=2,
            expected_parses=0,
        )
    ],
    ids=lambda case: case.description,
)
def test_given_one_edited_file_when_counting_then_only_that_file_re_evaluates(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    test_case: EditCountsTestCase,
) -> None:
    _ = generate_corpus(
        spec=CorpusSpec(target=tmp_path, file_target=test_case.file_target, seed=test_case.seed)
    )
    monkeypatch.chdir(tmp_path)
    _ = counted_check(argv=("--no-color", "--cache"))
    edited: Path = sorted(tmp_path.rglob("record_shaping.py"))[0]
    _ = appended_module_constant(path=edited)

    counts: dict[str, int] = counted_check(argv=("--no-color", "--cache"))

    assert counts[FRESH_EVALUATION_OPERATION] == test_case.expected_fresh_evaluations
    assert counts.get(PARSE_OPERATION, 0) == test_case.expected_parses


@pytest.mark.parametrize(
    "test_case",
    [
        ChurnCountsTestCase(
            description="all changed files avoid result reads and prefix scans",
            file_target=120,
            seed=0,
            expected_cache_record_reads=8,
            expected_cache_record_scans=0,
        )
    ],
    ids=lambda case: case.description,
)
def test_given_all_sources_changed_when_counting_then_cache_io_stays_generation_bounded(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    test_case: ChurnCountsTestCase,
) -> None:
    _ = generate_corpus(
        spec=CorpusSpec(target=tmp_path, file_target=test_case.file_target, seed=test_case.seed)
    )
    monkeypatch.chdir(tmp_path)
    _ = counted_check(argv=("--no-color", "--cache"))
    changed: tuple[Path, ...] = append_source_newlines(root=tmp_path)

    counts: dict[str, int] = counted_check(argv=("--no-color", "--cache"))

    assert counts[CACHE_RECORD_READ_OPERATION] == test_case.expected_cache_record_reads
    assert counts.get(CACHE_RECORD_SCAN_OPERATION, 0) == test_case.expected_cache_record_scans
    assert counts[FRESH_EVALUATION_OPERATION] == len(changed)
    assert counts[CACHE_RECORD_DELETE_OPERATION] == len(changed)
