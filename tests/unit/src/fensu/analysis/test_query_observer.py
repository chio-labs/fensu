"""Tests for the shared record/replay dependency-query observer."""

from __future__ import annotations

from pathlib import Path

import pytest

from fensu.analysis.classes.query_observer import QueryObserver
from fensu.cache.fingerprints.main.source import fingerprint_source
from fensu.evaluation._helpers.parsing import read_source_snapshot
from tests.unit.src.fensu.analysis._test_types import (
    ObserverFingerprintParityTestCase,
    ObserverQueryTestCase,
)


@pytest.mark.parametrize(
    "test_case",
    [
        ObserverFingerprintParityTestCase(
            description="observer parsing and cache fingerprints share one algorithm",
            source=b"value: int = 1\n",
            expected_available=True,
            expected_text="value: int = 1\n",
        )
    ],
    ids=lambda case: case.description,
)
def test_given_source_bytes_when_fingerprinting_then_all_implementations_agree(
    tmp_path: Path,
    test_case: ObserverFingerprintParityTestCase,
) -> None:
    path: Path = tmp_path / "models.py"
    path.write_bytes(test_case.source)
    observer: QueryObserver = QueryObserver()

    observed: str | None = observer.source_fingerprint(path=path)
    observed_text: tuple[str, str] | None = observer.source_text(path=path)

    assert (observed is not None) is test_case.expected_available
    assert observed_text is not None
    assert observed_text[0] == test_case.expected_text
    assert observed_text[1] == observed
    assert observed == read_source_snapshot(path=path).fingerprint
    assert observed == fingerprint_source(test_case.source).value


@pytest.mark.parametrize(
    "test_case",
    [
        ObserverQueryTestCase(
            description="observer answers listings globs probes and missing sources",
            file_names=("a.py", "b.py", "notes.txt"),
            directory_names=("pkg",),
            glob_pattern="*.py",
            glob_recursive=False,
            expected_entry_names=("a.py", "b.py", "notes.txt", "pkg"),
            expected_glob_names=("a.py", "b.py"),
            expected_missing_source=True,
        )
    ],
    ids=lambda case: case.description,
)
def test_given_project_layout_when_observing_queries_then_returns_expected_answers(
    tmp_path: Path,
    test_case: ObserverQueryTestCase,
) -> None:
    for file_name in test_case.file_names:
        (tmp_path / file_name).write_text("value: int = 1\n", encoding="utf-8")
    for directory_name in test_case.directory_names:
        (tmp_path / directory_name).mkdir()
    observer: QueryObserver = QueryObserver()

    entries: tuple[Path, ...] = observer.directory_entries(query_path=tmp_path)
    matches: tuple[Path, ...] = observer.glob(
        query_path=tmp_path,
        pattern=test_case.glob_pattern,
        recursive=test_case.glob_recursive,
    )
    missing: str | None = observer.source_fingerprint(path=tmp_path / "absent.py")

    assert tuple(sorted(entry.name for entry in entries)) == test_case.expected_entry_names
    assert tuple(sorted(match.name for match in matches)) == test_case.expected_glob_names
    assert observer.exists(resolved_path=tmp_path / test_case.file_names[0]) is True
    assert observer.is_file(resolved_path=tmp_path / test_case.file_names[0]) is True
    assert observer.is_dir(resolved_path=tmp_path / test_case.directory_names[0]) is True
    assert (missing is None) is test_case.expected_missing_source
