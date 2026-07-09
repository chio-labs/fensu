"""Tests for text report rendering."""

from __future__ import annotations

from pathlib import Path

import pytest

from strata.reporting.core.main.render import render
from strata.reporting.core.models import RenderedReport
from tests.unit.src.strata.reporting.core.main._test_types import RenderReportTestCase
from tests.unit.src.strata.reporting.core.main.helpers import (
    make_faults,
    make_missing_column_fault,
    make_missing_source_fault,
)


@pytest.mark.parametrize(
    "test_case",
    [
        RenderReportTestCase(
            description="plain text renders relative paths and summary",
            use_color=False,
            expected_text=(
                "XRP001  first\n"
                " --> src/pkg/a.py:2:4\n"
                "  |\n"
                "2 | beta = 2\n"
                "  |     ^\n"
                "  |\n"
                "\n"
                "XRP002  second\n"
                " --> src/pkg/b.py:-:-\n"
                "\n"
                "Found 2 faults"
            ),
            expected_fault_count=2,
        ),
        RenderReportTestCase(
            description="color emphasizes location code and unhealthy summary",
            use_color=True,
            expected_text=(
                "\033[1;38;5;208mXRP001\033[0m  first\n"
                "\033[2m --> src/pkg/a.py:2:4\033[0m\n"
                "\033[2m  |\033[0m\n"
                "\033[2m2 |\033[0m beta = 2\n"
                "\033[2m  |\033[0m     \033[1;38;5;208m^\033[0m\n"
                "\033[2m  |\033[0m\n"
                "\n"
                "\033[1;38;5;208mXRP002\033[0m  second\n"
                "\033[2m --> src/pkg/b.py:-:-\033[0m\n"
                "\n"
                "\033[1;38;5;208mFound 2 faults\033[0m"
            ),
            expected_fault_count=2,
        ),
    ],
    ids=lambda case: case.description,
)
def test_given_faults_when_rendering_report_then_returns_expected_text(
    tmp_path: Path,
    test_case: RenderReportTestCase,
) -> None:
    report: RenderedReport = render(
        faults=make_faults(tmp_path), root=tmp_path, use_color=test_case.use_color
    )

    assert report.text == test_case.expected_text
    assert report.fault_count == test_case.expected_fault_count


@pytest.mark.parametrize(
    "test_case",
    [
        RenderReportTestCase(
            description="missing source falls back to location only",
            use_color=False,
            expected_text="XRP003  missing source\n --> src/pkg/missing.py:1:0\n\nFound 1 fault",
            expected_fault_count=1,
        )
    ],
    ids=lambda case: case.description,
)
def test_given_missing_source_when_rendering_report_then_omits_source_excerpt(
    tmp_path: Path,
    test_case: RenderReportTestCase,
) -> None:
    report: RenderedReport = render(
        faults=make_missing_source_fault(tmp_path), root=tmp_path, use_color=test_case.use_color
    )

    assert report.text == test_case.expected_text
    assert report.fault_count == test_case.expected_fault_count


@pytest.mark.parametrize(
    "test_case",
    [
        RenderReportTestCase(
            description="missing column uses line excerpt with caret at column zero",
            use_color=False,
            expected_text=(
                "XRP004  line only\n"
                " --> src/pkg/line_only.py:1:-\n"
                "  |\n"
                "1 | line_only = True\n"
                "  | ^\n"
                "  |\n"
                "\n"
                "Found 1 fault"
            ),
            expected_fault_count=1,
        )
    ],
    ids=lambda case: case.description,
)
def test_given_line_without_column_when_rendering_report_then_uses_column_zero_caret(
    tmp_path: Path,
    test_case: RenderReportTestCase,
) -> None:
    report: RenderedReport = render(
        faults=make_missing_column_fault(tmp_path), root=tmp_path, use_color=test_case.use_color
    )

    assert report.text == test_case.expected_text
    assert report.fault_count == test_case.expected_fault_count


@pytest.mark.parametrize(
    "test_case",
    [
        RenderReportTestCase(
            description="color renders zero fault summary as healthy",
            use_color=True,
            expected_text="\033[1;32mFound 0 faults\033[0m",
            expected_fault_count=0,
        )
    ],
    ids=lambda case: case.description,
)
def test_given_no_faults_when_rendering_report_then_returns_healthy_summary(
    tmp_path: Path,
    test_case: RenderReportTestCase,
) -> None:
    report: RenderedReport = render(faults=(), root=tmp_path, use_color=test_case.use_color)

    assert report.text == test_case.expected_text
    assert report.fault_count == test_case.expected_fault_count
