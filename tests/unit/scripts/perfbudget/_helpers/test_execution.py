"""Tests for deterministic performance scenario source changes."""

from pathlib import Path

import pytest

from scripts.perfbudget._helpers.execution import _change_source_ratio, _read_max_rss
from tests.unit.scripts.perfbudget._helpers._test_types import (
    RssParseTestCase,
    SourceRatioChangeTestCase,
)


@pytest.mark.parametrize(
    "test_case",
    [
        SourceRatioChangeTestCase(
            description="one percent changes at least one source",
            file_count=100,
            numerator=1,
            denominator=100,
            expected_changed_count=1,
        ),
        SourceRatioChangeTestCase(
            description="fractional ratio rounds up to cover the requested share",
            file_count=7,
            numerator=75,
            denominator=100,
            expected_changed_count=6,
        ),
        SourceRatioChangeTestCase(
            description="complete churn changes every source",
            file_count=4,
            numerator=100,
            denominator=100,
            expected_changed_count=4,
        ),
    ],
    ids=lambda case: case.description,
)
def test_given_source_population_when_changing_ratio_then_changes_exact_deterministic_prefix(
    tmp_path: Path,
    test_case: SourceRatioChangeTestCase,
) -> None:
    paths: tuple[Path, ...] = tuple(
        tmp_path / f"source_{index:03d}.py" for index in range(test_case.file_count)
    )
    for path in paths:
        path.write_text("VALUE: int = 1\n", encoding="utf-8")

    changed: tuple[Path, ...] = _change_source_ratio(
        project=tmp_path,
        numerator=test_case.numerator,
        denominator=test_case.denominator,
    )

    assert len(changed) == test_case.expected_changed_count
    assert changed == paths[: test_case.expected_changed_count]


@pytest.mark.parametrize(
    "test_case",
    [
        RssParseTestCase(
            description="nonzero diagnostic exit prefix preserves final RSS value",
            output="Command exited with non-zero status 1\n123456\n",
            expected_max_rss_kib=123456,
        ),
        RssParseTestCase(
            description="empty timing output remains unavailable",
            output="",
            expected_max_rss_kib=None,
        ),
    ],
    ids=lambda case: case.description,
)
def test_given_gnu_time_output_when_reading_rss_then_returns_final_numeric_line(
    tmp_path: Path,
    test_case: RssParseTestCase,
) -> None:
    timing_path: Path = tmp_path / "rss.txt"
    timing_path.write_text(test_case.output, encoding="utf-8")

    max_rss_kib: int | None = _read_max_rss(timing_path=timing_path)

    assert max_rss_kib == test_case.expected_max_rss_kib
