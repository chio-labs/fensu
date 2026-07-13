"""Tests for text report rendering."""

from __future__ import annotations

from pathlib import Path

import pytest

from strata.reporting.main.render import render
from strata.reporting.models import RenderedReport
from tests.unit.src.strata.reporting.main._test_types import (
    ExceptionRenderTestCase,
    RemediationRenderTestCase,
    RenderReportTestCase,
    WarningRenderTestCase,
)
from tests.unit.src.strata.reporting.main.helpers import (
    make_faults,
    make_missing_column_fault,
    make_missing_source_fault,
    make_remediated_fault,
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


@pytest.mark.parametrize(
    "test_case",
    [
        WarningRenderTestCase(
            description="warning mode renders zero warning plural grammar",
            use_color=False,
            expected_text="Found 0 faults and 0 warnings",
            expected_fault_count=0,
            expected_warning_count=0,
        )
    ],
    ids=lambda case: case.description,
)
def test_given_no_findings_when_rendering_warning_mode_then_reports_both_zero_counts(
    tmp_path: Path,
    test_case: WarningRenderTestCase,
) -> None:
    report: RenderedReport = render(
        faults=(),
        warnings=(),
        root=tmp_path,
        use_color=test_case.use_color,
        show_warnings=True,
    )

    assert report.text == test_case.expected_text
    assert report.fault_count == test_case.expected_fault_count
    assert report.warning_count == test_case.expected_warning_count


@pytest.mark.parametrize(
    "test_case",
    [
        WarningRenderTestCase(
            description="one warning is labeled and keeps healthy colored summary",
            use_color=True,
            expected_text=(
                "  \033[2m= warning:\033[0m Move phase implementation into _helpers/ and keep "
                "main/ focused on ordered phase calls\n"
                "          that return explicit result models.\n\n"
                "\033[1;32mFound 0 faults and 1 warning\033[0m"
            ),
            expected_fault_count=0,
            expected_warning_count=1,
        )
    ],
    ids=lambda case: case.description,
)
def test_given_one_warning_when_rendering_colored_report_then_labels_nonblocking_finding(
    tmp_path: Path,
    test_case: WarningRenderTestCase,
) -> None:
    report: RenderedReport = render(
        faults=(),
        warnings=make_remediated_fault(tmp_path),
        root=tmp_path,
        use_color=test_case.use_color,
        show_warnings=True,
    )

    assert test_case.expected_text in report.text
    assert report.fault_count == test_case.expected_fault_count
    assert report.warning_count == test_case.expected_warning_count


@pytest.mark.parametrize(
    "test_case",
    [
        WarningRenderTestCase(
            description="mixed findings use independent plural summary counts",
            use_color=False,
            expected_text="Found 1 fault and 2 warnings",
            expected_fault_count=1,
            expected_warning_count=2,
        )
    ],
    ids=lambda case: case.description,
)
def test_given_fault_and_many_warnings_when_rendering_then_uses_independent_grammar(
    tmp_path: Path,
    test_case: WarningRenderTestCase,
) -> None:
    report: RenderedReport = render(
        faults=make_missing_source_fault(tmp_path),
        warnings=make_faults(tmp_path),
        root=tmp_path,
        use_color=test_case.use_color,
        show_warnings=True,
    )

    assert test_case.expected_text in report.text
    assert report.fault_count == test_case.expected_fault_count
    assert report.warning_count == test_case.expected_warning_count


@pytest.mark.parametrize(
    "test_case",
    [
        ExceptionRenderTestCase(
            description="applied exceptions appear after a healthy summary",
            applied_exception_count=2,
            expected_text="Found 0 faults\nApplied 2 rule exceptions",
        )
    ],
    ids=lambda case: case.description,
)
def test_given_applied_exceptions_when_rendering_then_reports_exception_count(
    tmp_path: Path,
    test_case: ExceptionRenderTestCase,
) -> None:
    report: RenderedReport = render(
        faults=(),
        root=tmp_path,
        applied_exception_count=test_case.applied_exception_count,
    )

    assert report.text == test_case.expected_text
    assert report.applied_exception_count == test_case.applied_exception_count


@pytest.mark.parametrize(
    "test_case",
    [
        RemediationRenderTestCase(
            description="plain diagnostics wrap remediation under a help label",
            use_color=False,
            expected_text_fragments=(
                "XRP005  main/ entry contains phase implementation",
                "  = help: Move phase implementation into _helpers/ and keep main/ focused on "
                "ordered phase calls",
                "          that return explicit result models.",
            ),
        ),
        RemediationRenderTestCase(
            description="colored diagnostics mute only the help label",
            use_color=True,
            expected_text_fragments=(
                "  \033[2m= help:\033[0m Move phase implementation into _helpers/ and keep "
                "main/ focused on ordered phase calls",
                "          that return explicit result models.",
            ),
        ),
    ],
    ids=lambda case: case.description,
)
def test_given_remediation_when_rendering_fault_then_separates_actionable_help(
    tmp_path: Path,
    test_case: RemediationRenderTestCase,
) -> None:
    report: RenderedReport = render(
        faults=make_remediated_fault(tmp_path), root=tmp_path, use_color=test_case.use_color
    )

    assert all(fragment in report.text for fragment in test_case.expected_text_fragments)
